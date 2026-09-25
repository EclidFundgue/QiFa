# Tiny Paper: A Minimal Example

## 1 Introduction

本文提出一个只用于测试的线性得分函数，用来给候选答案排序。

## 2 Method

给定候选 $x$ 与特征 $f(x)$，得分定义为：

$$ s(x) = w^\top f(x) + b \quad \text{(Eq.1)} $$

Fig.1 展示两阶段流程：先抽特征，再打分。Tab.1 给出测试用数字。
