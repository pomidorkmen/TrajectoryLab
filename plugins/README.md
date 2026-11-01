# User model directory

Iteration 1 defines the typed `BaseDragModel` contract and supplies examples in
`models_examples/`. The runtime plugin scanner, importlib loader, trust warning,
file hashing and UI refresh action are scheduled for iteration 3.

Do not place untrusted Python files here: Python plugins execute with the
permissions of the current user and are not sandboxed.
