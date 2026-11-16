(ns xray.metrics.complexity-integration-test
  (:require [babashka.fs :as fs]
            [clojure.test :refer [deftest is testing]]
            [xray.metrics.complexity :as complexity]))

(deftest clojure-and-javascript-share-the-complexity-contract
  (let [tmp (fs/create-temp-dir {:prefix "xray-complexity-integration-"})
        clj-path "src/demo/core.clj"
        js-path "src/demo/component.jsx"
        clj-file (fs/path tmp clj-path)
        js-file (fs/path tmp js-path)]
    (try
      (fs/create-dirs (fs/parent clj-file))
      (spit (str clj-file)
            "(ns demo.core)\n(defn decide [a b] (when a (when b :ok)))\n")
      (spit (str js-file)
            "export function Component({ok}) { if (ok) return <div>yes</div>; return <span>no</span>; }\n")

      (let [rows (complexity/complexity-functions (str tmp) [clj-path js-path])
            by-lang (group-by :lang rows)
            clj-row (first (get by-lang "clojure"))
            js-row (first (get by-lang "javascript"))]
        (testing "Clojure emits both CCN and CogC"
          (is (some? clj-row))
          (is (pos? (:cc clj-row)))
          (is (= 3 (:cognitive_complexity clj-row)))
          (is (= "rewrite-clj" (:analyzer clj-row))))

        (testing "JavaScript emits both CCN and CogC through Lizard"
          (is (some? js-row))
          (is (pos? (:cc js-row)))
          (is (pos? (:cognitive_complexity js-row)))
          (is (= "lizard+cognitive" (:analyzer js-row)))))
      (finally
        (fs/delete-tree tmp)))))
