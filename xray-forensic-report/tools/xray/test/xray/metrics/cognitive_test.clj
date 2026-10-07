(ns xray.metrics.cognitive-test
  (:require [clojure.test :refer [deftest is testing]]
            [xray.metrics.cognitive :as cognitive]))

(deftest linear-and-idiomatic-forms-stay-cheap
  (testing "linear code and threading do not add cognitive complexity"
    (is (= 0 (cognitive/complexity
              '(defn f [x] (-> x inc str))
              "f")))
    (is (= 0 (cognitive/complexity
              '(defn f [xs] (->> xs (map inc) (filter odd?) vec))
              "f")))))

(deftest branching-and-nesting-are-penalized
  (testing "when nested inside when pays a nesting penalty"
    (is (= 3 (cognitive/complexity
              '(defn f [a b]
                 (when a
                   (when b
                     :ok)))
              "f"))))
  (testing "if with a plain else charges the else branch"
    (is (= 2 (cognitive/complexity
              '(defn f [x]
                 (if x :yes :no))
              "f")))))

(deftest cond-and-case-have-different-reading-cost
  (testing "cond behaves like if/else-if/else"
    (is (= 3 (cognitive/complexity
              '(defn f [x]
                 (cond
                   (= x 1) :one
                   (= x 2) :two
                   :else :other))
              "f"))))
  (testing "case is switch-like and counts once"
    (is (= 1 (cognitive/complexity
              '(defn f [x]
                 (case x
                   1 :one
                   2 :two
                   :other))
              "f")))))

(deftest logical-sequences-count-by-operator-run
  (is (= 1 (cognitive/complexity
            '(defn f [a b c] (and a b c))
            "f")))
  (is (= 2 (cognitive/complexity
            '(defn f [a b c] (and a (or b c)))
            "f"))))

(deftest lambdas-add-nesting-without-own-increment
  (is (= 2 (cognitive/complexity
            '(defn f [xs]
               (map (fn [x]
                      (when x :ok))
                    xs))
            "f"))))

(deftest recursion-is-fundamental-not-multiplicative
  (testing "direct self recursion adds one point"
    (is (= 3 (cognitive/complexity
              '(defn f [n]
                 (if (zero? n)
                   0
                   (f (dec n))))
              "f"))))
  (testing "recur inside loop is represented by the loop itself"
    (is (= 1 (cognitive/complexity
              '(defn f [n]
                 (loop [i n]
                   (recur (dec i))))
              "f")))))
