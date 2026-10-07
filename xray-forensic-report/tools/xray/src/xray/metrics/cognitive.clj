(ns xray.metrics.cognitive)

(def ^:private if-forms #{"if" "if-not" "if-let" "if-some"})
(def ^:private when-forms #{"when" "when-not" "when-let" "when-some" "when-first"})
(def ^:private loop-forms #{"while" "doseq" "dotimes" "for" "loop" "go-loop"})
(def ^:private cond-forms #{"cond" "cond->" "cond->>"})
(def ^:private switch-forms #{"case" "condp"})
(def ^:private lambda-forms #{"fn" "fn*"})
(def ^:private logical-forms #{"and" "or"})

(defn- sym-name [x]
  (when (symbol? x) (name x)))

(defn- head-name [form]
  (when (seq? form) (sym-name (first form))))

(declare score*)

(defn- score-many [forms nesting fn-name]
  (reduce + 0 (map #(score* % nesting fn-name false) forms)))

(defn- else-if? [form]
  (contains? if-forms (head-name form)))

(defn- score-if [form nesting fn-name hybrid?]
  (let [[_ condition then-form else-form] form
        has-else? (>= (count form) 4)]
    (+ (if hybrid? 1 (inc nesting))
       (score* condition nesting fn-name false)
       (score* then-form (inc nesting) fn-name false)
       (if-not has-else?
         0
         (if (else-if? else-form)
           (score* else-form nesting fn-name true)
           (+ 1 (score* else-form (inc nesting) fn-name false)))))))

(defn- score-cond [form nesting fn-name]
  (let [head (head-name form)
        clauses (if (= head "cond") (rest form) (drop 2 form))
        prefix (if (= head "cond")
                 0
                 (score* (second form) nesting fn-name false))]
    (loop [pairs (seq (partition-all 2 clauses))
           first? true
           score prefix]
      (if-not pairs
        score
        (let [[[test expr] & more] pairs
              else? (= test :else)]
          (recur more
                 false
                 (+ score
                    (if first?
                      (if else? 1 (inc nesting))
                      1)
                    (if else? 0 (score* test nesting fn-name false))
                    (score* expr (inc nesting) fn-name false))))))))

(defn- alternating-results [clauses]
  (loop [xs (seq clauses) out []]
    (cond
      (nil? xs) out
      (nil? (next xs)) (conj out (first xs))
      :else (recur (nnext xs) (conj out (second xs))))))

(defn- score-case-like [form nesting fn-name]
  (let [head (head-name form)
        [prefix clauses] (if (= head "case")
                           [[(second form)] (drop 2 form)]
                           [[(second form) (nth form 2 nil)] (drop 3 form)])]
    (+ (inc nesting)
       (score-many prefix nesting fn-name)
       (score-many (alternating-results clauses) (inc nesting) fn-name))))

(defn- binding-score [binding-form nesting fn-name]
  (if-not (vector? binding-form)
    (score* binding-form nesting fn-name false)
    (loop [xs (seq binding-form) score 0]
      (if-not xs
        score
        (let [x (first xs)
              more (next xs)]
          (if (and (keyword? x)
                   (#{"when" "while"} (name x))
                   more)
            (recur (next more)
                   (+ score
                      1
                      (score* (first more) nesting fn-name false)))
            (recur more (+ score (score* x nesting fn-name false)))))))))

(defn- score-loop [form nesting fn-name]
  (let [[_ binding-or-test & body] form]
    (+ (inc nesting)
       (binding-score binding-or-test nesting fn-name)
       (score-many body (inc nesting) fn-name))))

(defn- score-try [form nesting fn-name]
  (reduce
   (fn [score part]
     (let [head (head-name part)]
       (+ score
          (cond
            (= head "catch")
            (let [[_ _class _binding & body] part]
              (+ (inc nesting)
                 (score-many body (inc nesting) fn-name)))

            (= head "finally")
            (score-many (rest part) nesting fn-name)

            :else
            (score* part nesting fn-name false)))))
   0
   (rest form)))

(defn- score-letfn [form nesting fn-name]
  (let [[_ bindings & body] form
        local-score
        (if (vector? bindings)
          (reduce
           (fn [score local-def]
             (+ score
                (if (seq? local-def)
                  (score-many (rest local-def) (inc nesting) fn-name)
                  (score* local-def nesting fn-name false))))
           0
           bindings)
          (score* bindings nesting fn-name false))]
    (+ local-score (score-many body nesting fn-name))))

(defn- score*
  [form nesting fn-name hybrid?]
  (cond
    (nil? form) 0
    (map? form) (score-many (mapcat identity form) nesting fn-name)
    (or (vector? form) (set? form)) (score-many form nesting fn-name)

    (seq? form)
    (let [head (head-name form)]
      (cond
        (contains? if-forms head)
        (score-if form nesting fn-name hybrid?)

        (contains? when-forms head)
        (let [[_ condition & body] form]
          (+ (inc nesting)
             (score* condition nesting fn-name false)
             (score-many body (inc nesting) fn-name)))

        (contains? cond-forms head)
        (score-cond form nesting fn-name)

        (contains? switch-forms head)
        (score-case-like form nesting fn-name)

        (contains? loop-forms head)
        (score-loop form nesting fn-name)

        (= head "try")
        (score-try form nesting fn-name)

        (= head "catch")
        (let [[_ _class _binding & body] form]
          (+ (inc nesting) (score-many body (inc nesting) fn-name)))

        (contains? lambda-forms head)
        (score-many (rest form) (inc nesting) fn-name)

        (= head "letfn")
        (score-letfn form nesting fn-name)

        (contains? logical-forms head)
        (+ (if (>= (count form) 3) 1 0)
           ;; Clojure's and/or are variadic. Nested use of the same operator
           ;; is still one logical sequence, while switching operator starts
           ;; a new sequence.
           (reduce
            + 0
            (map (fn [child]
                   (if (and (seq? child)
                            (= head (head-name child)))
                     (score-many (rest child) nesting fn-name)
                     (score* child nesting fn-name false)))
                 (rest form))))

        :else
        (score-many form nesting fn-name)))

    :else 0))

(defn- self-recursive?
  [form fn-name loop-depth]
  (cond
    (nil? form) false
    (map? form) (boolean (some #(self-recursive? % fn-name loop-depth)
                               (mapcat identity form)))
    (or (vector? form) (set? form))
    (boolean (some #(self-recursive? % fn-name loop-depth) form))

    (seq? form)
    (let [head (head-name form)]
      (cond
        (contains? lambda-forms head) false
        (= head "letfn")
        (boolean (some #(self-recursive? % fn-name loop-depth) (drop 2 form)))
        (= head "recur") (zero? loop-depth)
        (= head fn-name) true
        (#{"loop" "go-loop"} head)
        (boolean (some #(self-recursive? % fn-name (inc loop-depth)) (rest form)))
        :else
        (boolean (some #(self-recursive? % fn-name loop-depth) form))))

    :else false))

(defn complexity
  "Sonar-inspired Cognitive Complexity for one full Clojure defn form.

   Lisp policy:
   - flow-breaking forms are penalized, with nesting;
   - cond behaves like if/else-if, while case/condp behave like switch;
   - an and/or sequence costs one, not one per operand;
   - nested fn bodies add nesting but no increment;
   - direct self recursion or function-level recur costs one;
   - let/binding/threading/data-flow forms add no cost by themselves."
  [form fn-name]
  (let [name* (some-> fn-name str symbol name)
        body (drop 2 form)
        structural (score-many body 0 name*)]
    (+ structural
       (if (self-recursive? body name* 0) 1 0))))
