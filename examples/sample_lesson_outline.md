# Riemann Sums (AP Calculus AB - Unit 6.2)

## Essential question
How can we approximate the area under a curve when no closed-form integral is available?

## Key ideas
- Partition the interval [a, b] into n subintervals of width Δx = (b - a) / n.
- For each subinterval, pick a sample point x_i^* and form the rectangle of height f(x_i^*).
- The Riemann sum is S_n = Σ f(x_i^*) Δx.
- Left, right, midpoint, and upper/lower sums are special cases.
- As n → ∞, S_n → ∫_a^b f(x) dx (if f is integrable).

## Worked example
Approximate ∫_0^2 x^2 dx using a right Riemann sum with n = 4.
- Δx = 0.5; sample points x_i = 0.5, 1.0, 1.5, 2.0.
- S_4 = 0.5 (0.25 + 1 + 2.25 + 4) = 3.75.
- Exact value: 8/3 ≈ 2.667. So the right sum overestimates here.

## Common misconceptions
- Confusing Δx with the index variable.
- Forgetting to multiply each height by Δx.
- Thinking the midpoint rule is always exact (it isn't, just usually better than left/right).
