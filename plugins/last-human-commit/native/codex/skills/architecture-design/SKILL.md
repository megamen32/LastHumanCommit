---
name: architecture-design
description: Design a complete solution when an uncertain boundary or assumption would make implementation expensive to redo.
---

# Architecture design

Start from the requested behavior and the existing system. Identify the decisions that would be expensive to reverse: interfaces, ownership of data, lifecycle, deployment or failure handling. A clear local change needs little design.

For fullcycle work, first prepare exactly three short approach summaries and show their differences and a recommendation. Wait for the user's explicit choice, as described in `plan`, before detailed design, decomposition, parallel allocation or implementation. Limited read-only investigation can establish the facts needed for the choice. Develop the selected approach and remove optional work while keeping the accepted outcome. An ideal design can expose useful choices; it is a reference, not a second implementation.

For an uncertain decision, run a small experiment whose result can choose between the alternatives. Use an Adviser, Critic or `council` when another perspective can change the route. Resolve material findings and move on once the next investment is justified.

After the user's fullcycle choice, build an early path through the real entry point and important boundaries. Identify simulated dependencies and the gaps still to be implemented. Split the remaining work by ownership and dependencies with `plan`; use `model-routing` for suitable executors.

Keep the selected design, decisive evidence and deferred choices in the existing task record. After delivery, save lessons that will help a later task.
