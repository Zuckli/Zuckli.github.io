---
title: "{{ replace .File.ContentBaseName "-" " " | title }}"
date: {{ .Date }}
draft: true
tags: []
categories: []
description: ""
summary: ""
comments: true
ShowToc: true
math: false
---

## 小节标题

正文从这里开始。

<!-- 需要公式时把 math 改成 true，然后：

行内公式 $E = mc^2$，块级公式：

$$
\int_0^1 x^2 \, dx = \frac{1}{3}
$$
-->