![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
[![Build Status](https://travis-ci.org/anfederico/clairvoyant.svg?branch=master)](https://travis-ci.org/anfederico/clairvoyant)
![Contributions welcome](https://img.shields.io/badge/contributions-welcome-orange.svg)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/Naereen/StrapDown.js/graphs/commit-activity)
[![Awesome](https://cdn.rawgit.com/sindresorhus/awesome/d7305f38d29fed78fa85652e3a63e154dd8e8829/media/badge.svg)](https://github.com/sindresorhus/awesome)

<a name="readme-top"></a>

# Blender Voxel Tools

## Prerequisites

**Blender Version:**

This addon is designed for recent versions of Blender. For the best experience and compatibility, please use:

* The **latest stable version of Blender available on Steam**. This is often the easiest way to install and keep Blender updated.
* Alternatively, if downloading from the official Blender website, we recommend using a recent stable version, for example, **Blender 4.1 or newer**. (The user originally mentioned targeting a version like 4.4, so ensure you are using a version that meets the addon's compatibility requirements).

**How to Get Blender:**

1.  **Option 1: Steam:**
    * Open the Steam client.
    * Search for "Blender" in the store.
    * Install it like any other Steam application.

2.  **Option 2: Official Blender Website:**
    * Go to the official Blender download page: [https://www.blender.org/download/](https://www.blender.org/download/)
    * Download the installer or portable version suitable for your operating system (e.g., for Blender 4.1 or the specific version you intend to use).
    * Follow the installation instructions provided on the website.

## Overview

Blender Voxel Tools is an addon for Blender that provides a suite of utilities for processing, visualizing, and analyzing 3D voxel data. It allows users to:

* Import voxel data from `.npy` or text files.
* Generate 3D meshes from voxel data using different strategies.
* Analyze voxel structures by counting connected components of solid material.
* Identify and count enclosed empty spaces ("bubbles") within the voxel data.

The addon adds a new panel to the Blender 3D View's UI for easy access to its features.

## Features

* **Custom UI Panel**: "Voxel Tools" panel in the 3D View (N-Panel) for all operations.
* **Flexible Voxel Input**:
    * Load voxel data from NumPy binary files (`.npy`) or comma-separated text files.
    * Specify voxel grid dimensions (depth, height, width) or use a uniform size.
* **Mesh Generation**:
    * **Optimized Shell Mesh (`Process Voxel Data` button)**: Creates a 3D mesh representing the surface of the voxel data. This method intelligently shares vertices and removes internal faces to produce a clean, manifold-ready shell.
    * **Simple Cube Mesh (`Process Voxel Data Complete` button)**: Creates a 3D mesh where each surface voxel is represented by a distinct cube. This method is simpler and results in a collection of cubes rather than a continuous shell.
* **Material Application**: Automatically applies a basic material with user-defined RGB color to the generated mesh.
* **Camera Setup**: Adds a camera to the scene, positioned to view the generated object.
* **OBJ Export**: Exports the generated mesh to an `.obj` file with a report of the file size.
* **Connectivity Analysis**:
    * **Count Connected Components**: Identifies and counts distinct groups of connected 'solid' (value 1) voxels.
    * **Count Bubbles**: Identifies and counts enclosed 'empty' (value 0) regions completely surrounded by solid voxels.
    * Supports 6-connectivity, 18-connectivity, and 26-connectivity for both analyses.
* **Results Display**: Shows the counts for connected components and bubbles directly in the UI panel.
* **Performance Metrics**: Reports execution time for mesh generation and analysis tasks.

## Installation

1.  Download the Python script (`.py` file containing this addon).
2.  Open Blender.
3.  Go to `Edit` > `Preferences...` > `Add-ons`.
4.  Click `Install...` and navigate to the downloaded `.py` file. Select it and click `Install Add-on`.
5.  Enable the addon by checking the box next to its name ("Object: Voxel Tools" or similar, based on how it's registered).

## How to Use

Once installed and enabled, the "Voxel Tools" panel will appear in the UI region of the 3D Viewport. You can toggle this region by pressing the `N` key.

### The "Voxel Tools" Panel

The panel is organized into several sections:

1.  **File Path Input**:
    * `Voxel File Path`: Click the folder icon to browse and select your voxel data file. Supported formats are `.npy` and comma-separated text files.

2.  **Resolution Settings**:
    * `Synchronize Dimensions`:
        * If checked, uses a single `Uniform Size` value for depth, height, and width of the voxel grid.
        * If unchecked, allows you to specify `Depth`, `Height`, and `Width` individually.
    * `Uniform Size`: The size for all dimensions when synchronized.
    * `Depth`, `Height`, `Width`: Individual dimensions for the voxel grid.

3.  **Color Settings**:
    * `R`, `G`, `B`: Define the Red, Green, and Blue components for the material applied to the generated mesh. These values should be between 0.0 and 1.0.

4.  **Mesh Generation Buttons**:
    * `Process Voxel Data`: Click this to generate an optimized shell mesh from the surface voxels. This version is generally recommended for creating a clean, single object representing the voxel data's exterior.
    * `Process Voxel Data Complete`: Click this to generate a mesh where each surface voxel becomes a separate (though potentially touching) cube. This results in a different type of visualization.
    * **Note**: Both operators will first clear the current Blender scene of all objects.

5.  **Count Connected Components**:
    * Buttons: `6-Connectivity`, `18-Connectivity`, `26-Connectivity`.
    * Clicking one of these buttons will analyze the 'solid' (value 1) voxels in the loaded data file and count how many separate groups of connected voxels exist, based on the chosen connectivity rule.
    * **Connectivity Types**:
        * `6-Connectivity`: Voxels are connected if they share a face.
        * `18-Connectivity`: Voxels are connected if they share a face or an edge.
        * `26-Connectivity`: Voxels are connected if they share a face, an edge, or a vertex.

6.  **Count Bubbles**:
    * Buttons: `6-Connectivity`, `18-Connectivity`, `26-Connectivity`.
    * Clicking one of these buttons will analyze the 'empty' (value 0) voxels to find regions completely enclosed by 'solid' voxels. The connectivity type refers to how the empty voxels connect to form a bubble and how solid voxels connect to enclose it.

7.  **Results Display**:
    * `Connected Components Count`: Shows the latest counts for 6, 18, and 26-connectivity analyses.
    * `Bubbles Count`: Shows the latest counts for 6, 18, and 26-connectivity bubble analyses.

### Workflow

1.  Set the `Voxel File Path` to your data file.
2.  Configure the `Resolution Settings` to match your data's dimensions.
3.  Adjust `Color Settings` for the desired mesh color.
4.  Click one of the "Process Voxel Data" buttons to generate a mesh.
5.  Optionally, use the "Count Connected Components" or "Count Bubbles" buttons to analyze the voxel data. Results will appear in the panel.

### Output

* A 3D mesh object is added to the Blender scene.
* A camera is set up.
* An `.obj` file of the generated mesh is exported to a hardcoded path (see "Important Notes").
* Information messages (execution time, file sizes, analysis results) are displayed in the Blender Info editor and briefly at the bottom of the 3D View.

## Expected Voxel File Format

* **`.npy` files**: Binary files saved using NumPy (`numpy.save()`). The data should be a 3D NumPy array of unsigned 8-bit integers (`np.uint8`), where `1` represents a solid voxel and `0` represents an empty space. The array should be flattened or reshapeable to the specified Depth, Height, and Width. The `ProcessVoxelDataOperator` handles this format.
* **Text files (e.g., `.csv`, `.txt`)**: Plain text files where voxel values are typically comma-separated. Each value should be interpretable as an integer (0 or 1). The data is read as a flat list and then reshaped according to the provided dimensions. Both mesh generation operators can read this, though `ProcessVoxelDataOperator` expects `uint8` values.

The script assumes the input data (after reshaping) is oriented such that it might need a 90-degree rotation around one axis to align with Blender's coordinate system; this rotation is applied internally (`np.rot90(data, k=1, axes=(1, 2))`).

## Important Notes & Known Issues

* **Scene Clearing**: Both mesh generation operators (`Process Voxel Data` and `ProcessVoxelDataOperatorComplete`) **will delete all objects currently in your Blender scene** before generating the new mesh. Save your work before using these operators if you have other objects in the scene.
* **Hardcoded Export Path**: The generated `.obj` file is saved to a hardcoded path (e.g., `C:\Users\Slaye\OneDrive\Escritorio\Test.obj` or `Test_1.obj`). You will need to modify the script if you want to change this path or implement a file dialog for saving.
* **Color Input**: The `R, G, B` color properties in the UI are `FloatProperty` types, expecting values between 0.0 and 1.0. The script internally uses `int()` on these values when retrieving them in the `ProcessVoxelDataOperator` and `ProcessVoxelDataOperatorComplete` operators. This means if you input, for example, `0.5` for Red, it will be converted to `0`, resulting in black. For correct color representation, ensure your R, G, B inputs are exactly `1.0` for full intensity of that component, or modify the script to use the float values directly (e.g., `red_color = context.scene.red_color` without the `int()` cast).
* **Mesh Generation Differences**:
    * `Process Voxel Data`: Aims to create an optimized, manifold shell of the voxel object. It's generally preferred for a clean visual representation.
    * `ProcessVoxelDataOperatorComplete`: Creates a simpler representation where each surface voxel is an independent cube with all its faces. This will result in a higher vertex/face count and overlapping internal faces if voxels are adjacent.
* **File Loading in `ProcessVoxelDataOperatorComplete`**: This operator currently only loads data using `np.loadtxt` and does not explicitly handle `.npy` files or `dtype=np.uint8` like the other operator.
* **Multiprocessing Imports**: The script imports `multiprocessing` utilities, but they are not used in the visible parts of the provided code. They might be intended for future optimizations.

## Core Algorithms and Techniques

* **NumPy**: Heavily used for efficient array manipulation, including:
    * Loading and reshaping data.
    * Padding arrays to simplify boundary conditions.
    * Calculating neighbor sums using array slicing (`ProcessVoxelDataOperator`) or `np.roll` (`ProcessVoxelDataOperatorComplete`) for surface detection.
* **Surface Voxel Detection**: Voxels are typically identified as surface voxels if they are 'solid' (value 1) and have fewer than 6 solid neighbors (for 6-connectivity).
* **Mesh Construction (`ProcessVoxelDataOperator`)**:
    * Unique vertices are stored and reused (`vertex_map`).
    * Faces are generated for each surface voxel cube.
    * Internal faces (faces shared by two cubes) are identified and removed by counting face occurrences (`face_count`), resulting in an external shell.
* **Breadth-First Search (BFS)**: Used in `BaseCountConnectedComponentsOperator` and `BaseCountBubblesOperator` to explore connected regions of voxels.
    * For connected components, BFS starts from an unvisited solid voxel and finds all reachable solid voxels.
    * For bubbles, BFS starts from an unvisited empty voxel and explores reachable empty voxels, checking if the explored region touches the boundary of the voxel grid. If it doesn't, it's considered an enclosed bubble.

---

## Co-authors

- Dr. Hermilo Sanchez Cruz

### Built With

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)&nbsp;

### Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

### 🤝🏻 &nbsp;Connect with Me

<p align="center">
<a href="https://www.linkedin.com/in/cesar-eduardo-mu%C3%B1oz-chavez-a00674186/"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white"/></a>
<a href="https://twitter.com/CesarEd43166481"><img src="https://img.shields.io/badge/Twitter-1DA1F2?style=for-the-badge&logo=twitter&logoColor=white"/></a>