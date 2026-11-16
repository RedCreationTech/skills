(ns xray.metrics.complexity
  (:require [babashka.fs :as fs]
            [babashka.process :as p]
            [cheshire.core :as json]
            [clojure.string :as str]
            [xray.metrics.cognitive :as cognitive]
            [rewrite-clj.node :as node]
            [rewrite-clj.parser :as parser]))

(def ^:private clj-exts #{"clj" "cljs" "cljc"})

(def ^:private lizard-exts
  ;; React is covered through JS/JSX/TS/TSX. Vue SFC is covered by .vue.
  #{"js" "jsx" "ts" "tsx" "vue" "java" "cs"})

(def ^:private valid-def-forms
  #{'defn 'defn- 'defstate})

(def ^:private cc-inc-forms
  ;; Minimal Clojure set; the non-Clojure backend uses Lizard's language parsers.
  #{'if 'when 'cond 'case 'when-let 'if-let 'when-some})

(defn- extension [path]
  (some-> (fs/extension path) str/lower-case))

(defn- clj-file? [path]
  (contains? clj-exts (extension path)))

(defn- lizard-file? [path]
  (contains? lizard-exts (extension path)))

(defn- node-type
  "Return first symbol of list-like node, or nil."
  [n]
  (try
    (-> n :children first :value)
    (catch Exception _ nil)))

(defn- non-ws-children [n]
  (->> (:children n)
       (remove node/whitespace?)
       (remove node/comment?)))

(defn- defn-node? [n]
  (contains? valid-def-forms (node-type n)))

(defn- fn-name [defn-node]
  (try
    (let [c (non-ws-children defn-node)
          nm (second c)]
      (when nm
        (str (node/sexpr nm))))
    (catch Exception _ nil)))

(declare node-cc)

(defn- cc-inc? [n]
  (contains? cc-inc-forms (node-type n)))

(defn- node-cc
  "Compute cyclomatic complexity increments within node (not counting base 1)."
  [n]
  (let [kids (or (:children n) [])]
    (reduce
     (fn [r k]
       (+ r (node-cc k)))
     (if (cc-inc? n) 1 0)
     kids)))

(defn- analyze-clojure-file [repo path]
  (let [abs (str (fs/path repo path))]
    (when (and (clj-file? path) (fs/exists? abs))
      (try
        (let [code (slurp abs)
              parsed (parser/parse-string-all code)
              top (filter defn-node? (:children parsed))]
          (->> top
               (mapv (fn [n]
                       (let [nm (fn-name n)
                             cc (+ 1 (node-cc n))
                             form (try (node/sexpr n) (catch Exception _ nil))
                             cogc (if (and nm (seq? form))
                                    (cognitive/complexity form nm)
                                    0)]
                         (when nm
                           {:path path
                            :fn nm
                            :long_name nm
                            :cc cc
                            :cognitive_complexity cogc
                            :nloc nil
                            :tokens nil
                            :params nil
                            :start_line nil
                            :end_line nil
                            :lang "clojure"
                            :analyzer "rewrite-clj"}))))
               (remove nil?)
               vec))
        (catch Exception _e
          ;; Skip one malformed Clojure file and keep the repo-level pipeline alive.
          [])))))

(defn- tool-root-from-source []
  ;; .../tools/xray/src/xray/metrics/complexity.clj -> .../tools/xray
  (some-> *file*
          fs/path
          fs/parent
          fs/parent
          fs/parent
          fs/parent))

(defn- tool-root-from-config []
  (when-let [config (System/getProperty "babashka.config")]
    (let [p (fs/path config)
          parent (fs/parent p)]
      (when (and parent (fs/regular-file? (fs/path parent "bb.edn")))
        parent))))

(defn- find-lizard-helper []
  (let [source-root (tool-root-from-source)
        config-root (tool-root-from-config)
        env-root (some-> (System/getenv "XRAY_TOOL_ROOT") fs/path)
        cwd (fs/cwd)
        candidates (remove nil?
                           [(when env-root
                              (fs/path env-root "scripts" "complexity_lizard.py"))
                            (when config-root
                              (fs/path config-root "scripts" "complexity_lizard.py"))
                            (when source-root
                              (fs/path source-root "scripts" "complexity_lizard.py"))
                            ;; Running tests from the skills repository root.
                            (fs/path cwd "xray-forensic-report" "tools" "xray"
                                     "scripts" "complexity_lizard.py")
                            ;; Running from the XRay tool root or its parent.
                            (fs/path cwd "scripts" "complexity_lizard.py")
                            (fs/path cwd "tools" "xray" "scripts" "complexity_lizard.py")])]
    (some (fn [candidate]
            (when (fs/regular-file? candidate)
              (str candidate)))
          candidates)))

(defn- python-command []
  (or (some-> (fs/which "python3") str)
      (some-> (fs/which "python") str)))

(defn- warn-lizard-errors! [errors]
  (doseq [{:keys [path error]} errors]
    (binding [*out* *err*]
      (println (str "[WARN] XRay complexity skipped " path ": " error)))))

(defn- analyze-lizard-files [repo paths]
  (if (empty? paths)
    []
    (let [helper (find-lizard-helper)
          python (python-command)]
      (when-not helper
        (throw (ex-info
                "XRay multi-language complexity helper was not found. Expected scripts/complexity_lizard.py under the XRay tool root."
                {:repo repo :paths (count paths)})))
      (when-not python
        (throw (ex-info
                "Python 3 is required for JS/TS/Vue/Java/C# complexity analysis."
                {:repo repo :paths (count paths)})))
      (let [tmp (java.io.File/createTempFile "xray-complexity-" ".txt")]
        (try
          (spit tmp (str (str/join "\n" paths) "\n"))
          (let [result (p/sh {:out :string :err :string :continue true}
                             python helper
                             "--repo" (str (fs/absolutize repo))
                             "--file-list" (.getAbsolutePath tmp))
                exit (:exit result)
                stdout (:out result)
                stderr (:err result)]
            (when-not (zero? exit)
              (throw (ex-info
                      (str "Multi-language complexity analysis failed. "
                           (str/trim (or stderr ""))
                           " Install the pinned Python dependency with: "
                           "python3 -m pip install lizard==1.24.1")
                      {:exit exit :stderr stderr})))
            (let [payload (json/parse-string stdout true)
                  errors (or (:errors payload) [])]
              (warn-lizard-errors! errors)
              (vec (or (:functions payload) []))))
          (finally
            (.delete tmp)))))))

(defn complexity-functions
  "Compute function-level complexity for supported repo-relative paths.

   Native Clojure support:
   - .clj, .cljs, .cljc via rewrite-clj

   Lizard-backed support:
   - .js, .jsx, .ts, .tsx (including React)
   - .vue (Vue SFC)
   - .java
   - .cs (C#)

   Rows preserve the original :path/:fn/:cc/:lang contract and add
   :cognitive_complexity, :long_name, :nloc, :tokens, :params,
   :start_line, :end_line, :analyzer
   when the backend can provide them."
  [repo paths]
  (let [paths (->> paths distinct vec)
        clj-paths (filterv clj-file? paths)
        lizard-paths (filterv lizard-file? paths)
        clj-rows (mapcat #(analyze-clojure-file repo %) clj-paths)
        lizard-rows (analyze-lizard-files repo lizard-paths)]
    (->> (concat clj-rows lizard-rows)
         (sort-by (juxt :path
                        (fn [row] (or (:start_line row) Long/MAX_VALUE))
                        :fn))
         vec)))
