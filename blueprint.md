# Nano Banana Pro - Image Batch Processor Blueprint

## Overview
A web-based batch processing tool designed to interface with the "Nano Banana Pro" AI image generation service. It allows users to upload large batches of reference images (50-100+), define up to 4 specific prompts, and processes them in strict batches of 4 to respect API rate limits. Generated images (1600x1600px) are automatically saved to a user-selected local directory.

## Features
- **Batch Upload**: Support for selecting multiple image files at once.
- **Prompt Management**: 4 dedicated input fields for generation prompts.
- **Concurrency Control**: Strict limit of 4 simultaneous generations.
- **Auto-Save**: Uses the File System Access API to save results directly to a local folder without repetitive dialogs.
- **Visual Feedback**: Real-time progress tracking and image preview.
- **Placeholder Generation**: (Currently simulated) Produces 1600x1600 placeholder images for testing workflow.

## Plan
1.  **UI Implementation**: Create a professional, dark-themed interface with queue status, prompt inputs, and a gallery.
2.  **Logic Core**: Implement a `BatchProcessor` class in `main.js` to handle the queue.
3.  **File System Integration**: Implement `showDirectoryPicker` for seamless saving.
4.  **Mock API**: Create a dummy function to simulate the 1600x1600 rendering delay.
