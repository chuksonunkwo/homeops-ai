# HomeOps v0.4 UX Direction

## North star

Every customer screen should answer three questions:

1. What is happening?
2. Do I need to do anything?
3. What should I do next?

## 3-second rule

The default landing communicates only:

- **Where am I?** HomeOps.
- **What is this for?** Home repairs, handled.
- **What should I do?** Tell HomeOps what needs fixing.

Technical hackathon evidence is hidden behind **View demo details**.

## Progressive disclosure

- Before a request: no workflow dashboard, quotes, invoice metrics or developer status.
- Quotes ready: show one recommendation first; compare-all is secondary.
- Booked: show provider, visit window and agreed price.
- Service complete: prompt to check final bill.
- Cost exception: show agreed price, final bill and extra cost in plain English.
- Closed: confirm outcome and offer a new repair.

## Terminology changes

| Old | v0.4 |
| --- | --- |
| Control Tower | Your repair |
| Commercial Evaluation | Compare providers |
| Approved baseline | Agreed price |
| Invoice | Final bill |
| Variance | Extra cost |
| Request justification | Ask provider to explain |
| Approve variance | Approve extra cost |
| Voice Simulator | HomeOps Assistant |

## Accessibility

- visible keyboard focus
- skip-to-content link
- 44px minimum control targets
- non-colour status text
- responsive mobile flow
- reduced-motion preference respected
- polite live regions for dynamic updates
- plain-language error recovery
