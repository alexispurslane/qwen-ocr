#!/usr/bin/env uv run python
"""Demo script to show the new TableUI with scrolling output window"""

import time
import random
from ui import TableUI, BatchStatus


def demo_table_ui():
    """Demonstrate the TableUI with mock processing and scrolling output"""

    # Create the UI instance with scrolling window
    table_ui = TableUI(scroll_window_height=8)

    # Create some mock batches
    batches_info = [
        (0, 1, 10),  # Batch 0: Pages 1-10
        (1, 11, 20),  # Batch 1: Pages 11-20
        (2, 21, 30),  # Batch 2: Pages 21-30
        (3, 31, 40),  # Batch 3: Pages 31-40
    ]

    print("Creating batch info...")
    for batch_num, page_start, page_end in batches_info:
        table_ui.create_batch_info(batch_num, page_start, page_end)
    table_ui.render_table()
    time.sleep(2)

    print("\nStarting batch processing simulation with scrolling output...")

    # Sample OCR outputs for each batch
    sample_outputs = [
        # Batch 1: Introduction to Machine Learning
        """# Introduction to Machine Learning

Machine learning is a subset of artificial intelligence that focuses on the development of computer systems that can learn and improve their performance on a specific task through experience without being explicitly programmed.

## Key Concepts

**Supervised Learning**: This type of learning uses labeled training data to learn a mapping function from input variables to output variables.

**Unsupervised Learning**: Finding hidden patterns in data without labeled examples.

### Applications

- Image recognition
- Natural language processing
- Recommendation systems
- Fraud detection

---

""",
        # Batch 2: Supervised Learning Algorithms
        """## Supervised Learning Algorithms

In this chapter, we explore various supervised learning algorithms that form the foundation of modern machine learning applications.

### Linear Regression

Linear regression attempts to model the relationship between variables by fitting a linear equation to observed data.

**Equation**: y = mx + b

Where:
- y is the dependent variable
- x is the independent variable  
- m is the slope of the line
- b is the y-intercept

### Decision Trees

Decision trees are a non-parametric supervised learning method used for classification and regression. The goal is to create a model that predicts the target value by learning simple decision rules inferred from data features.

### Support Vector Machines

Support Vector Machines (SVM) are powerful classifiers that work well on high-dimensional datasets. They find the optimal hyperplane that separates different classes.

""",
        # Batch 3: Neural Network Architectures
        """## Neural Network Architectures

Neural networks are computing systems inspired by biological neural networks that constitute animal brains.

### Perceptron

The perceptron is the simplest type of feedforward neural network. It was developed by Frank Rosenblatt in 1957 and consists of a single layer of weights that transform the input.

### Multilayer Perceptron

A multilayer perceptron (MLP) is a class of feedforward artificial neural network. An MLP consists of at least three layers of nodes: an input layer, a hidden layer, and an output layer.

**Activation Functions**:
- Sigmoid: σ(x) = 1 / (1 + e^(-x))
- ReLU: f(x) = max(0, x)
- Tanh: tanh(x) = (e^x - e^(-x)) / (e^x + e^(-x))

### Convolutional Neural Networks

CNNs are particularly effective for processing grid-like data such as images. They use a mathematical operation called convolution instead of general matrix multiplication.

""",
        # Batch 4: Optimization Techniques
        """## Optimization Techniques

Optimization is crucial for training effective machine learning models. This section covers the mathematical foundations and practical implementations.

### Gradient Descent

Gradient descent is a first-order iterative optimization algorithm for finding the minimum of a function. In machine learning, we use it to minimize the loss function.

**Update Rule**:
θ = θ - α * ∇J(θ)

Where:
- θ represents the parameters
- α is the learning rate
- ∇J(θ) is the gradient of the cost function

### Stochastic Gradient Descent

SGD updates parameters using only a single training example at each iteration, making it faster for large datasets.

### Adam Optimizer

Adam (Adaptive Moment Estimation) combines ideas from RMSprop and momentum to provide an optimization algorithm that can handle sparse gradients on noisy problems.

**Key Benefits**:
- Computationally efficient
- Requires little memory
- Works well with default parameters

---

In conclusion, understanding these optimization techniques is essential for developing robust machine learning models that can generalize well to new data.
""",
    ]

    for batch_num, page_start, page_end in batches_info:
        # Mark as in progress
        table_ui.start_batch(batch_num)
        table_ui.render_table()

        # Simulate processing time
        time.sleep(random.uniform(1, 3))

        # Update with input tokens
        input_tokens = random.randint(800, 1200)
        table_ui.update_batch_tokens(batch_num, input_tokens)
        table_ui.render_table()

        # Simulate API call time
        time.sleep(random.uniform(2, 4))

        # Complete with output
        responses = [
            "This document provides an introduction to machine learning concepts...",
            "Chapter 2 discusses various supervised learning algorithms...",
            "The following section covers neural network architectures...",
            "In conclusion, this chapter summarizes key optimization techniques...",
        ]
        output_tokens = random.randint(1200, 1800)
        # Ensure different responses for each batch
        preview = responses[batch_num % len(responses)]
        table_ui.complete_batch(batch_num, output_tokens, preview)

        # Add the sample OCR output to the scrolling window
        table_ui.add_output_text(sample_outputs[batch_num])

        table_ui.render_table()

        time.sleep(1)

    # Show final results
    table_ui.display_final_results("demo_output.md", 40, 4)


if __name__ == "__main__":
    demo_table_ui()
