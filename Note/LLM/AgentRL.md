# GRPO
从理论角度来讲，就是根据不同的trajectory计算得出不同的reward。和PPO不一样的点在于对整个输出计算reward而不是为输出的每一个token分别计算token。直觉上看确实更适合LLM的训练。

具体来讲，每一个trajectory的reward的计算思路是reward减去mean(rewards)/std(rewards).之后，再使用得到的reward以重要性采样的方式计算损失：

$J_{GRPO}$ = $\frac{1}{N}$ * $\sum_{i=1}^n$ $\sum_{t=1}^{T_n}$ min($A_{\theta^‘}^{GRPO}$ ($s_{t}^n,a_{t}^n$)$\frac{P_{\theta}(s_{t}^n,a_{t}^n)}{P_{\theta^‘}(s_{t}^n,a_{t}^n)}$)

在实验中，一般只关注trajectory的生成以及reward model。