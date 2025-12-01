#!/usr/bin/env uv run python
"""Demo script to show the new TableUI in action"""

import time
import random
from ui import TableUI, BatchStatus


def demo_table_ui():
    """Demonstrate the TableUI with mock processing"""

    # Create the UI instance
    table_ui = TableUI()

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

    print("\nStarting batch processing simulation...")

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
        table_ui.render_table()

        time.sleep(1)

    # Show final results
    table_ui.display_final_results("demo_output.md", 40, 4)


if __name__ == "__main__":
    demo_table_ui()
