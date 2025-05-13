# ----------------------------
#  Standard Library Imports
# ----------------------------
import os
import bpy
import multiprocessing

from collections import deque
from queue import Queue

import time
from multiprocessing import Pool, cpu_count

# ----------------------------
#  Third-Party Library Imports
# ----------------------------
import numpy as np

# ----------------------------
#  Project-Specific Imports
# ----------------------------

class VoxelProcessingPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties"""
    bl_label = "Voxel Processing"
    bl_idname = "OBJECT_PT_voxel_processing"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Voxel Tools'

    def draw(self, context):
        """Draw the UI elements in the panel."""
        layout = self.layout
        scene = context.scene

        # File path input
        layout.prop(scene, "voxel_file_path")

        # Section for resolution
        layout.label(text="Resolution Settings")
        layout.prop(scene, "synchronize_dimensions")

        if scene.synchronize_dimensions:
            layout.prop(scene, "voxel_uniform_size")
        else:
            layout.prop(scene, "voxel_depth")
            layout.prop(scene, "voxel_height")
            layout.prop(scene, "voxel_width")

        # Section for colors
        layout.label(text="Color Settings")
        layout.prop(scene, "red_color")
        layout.prop(scene, "green_color")
        layout.prop(scene, "blue_color")

        # Button to execute the processing
        layout.operator("object.process_voxel_data")
        layout.operator("object.process_voxel_data_complete")

        # Buttons for counting connected components
        layout.label(text="Count Connected Components")
        layout.operator("object.count_connected_components_6", text="6-Connectivity")
        layout.operator("object.count_connected_components_18", text="18-Connectivity")
        layout.operator("object.count_connected_components_26", text="26-Connectivity")

        # Buttons for counting bubbles
        layout.label(text="Count Bubbles")
        layout.operator("object.count_bubbles_6", text="6-Connectivity")
        layout.operator("object.count_bubbles_18", text="18-Connectivity")
        layout.operator("object.count_bubbles_26", text="26-Connectivity")

        # Display connected components results
        layout.label(text="Connected Components Count:")
        layout.label(text=f"6-Connectivity: {scene.components_6}")
        layout.label(text=f"18-Connectivity: {scene.components_18}")
        layout.label(text=f"26-Connectivity: {scene.components_26}")

        # Display bubbles results
        layout.label(text="Bubbles Count:")
        layout.label(text=f"6-Bubbles: {scene.bubbles_6}")
        layout.label(text=f"18-Bubbles: {scene.bubbles_18}")
        layout.label(text=f"26-Bubbles: {scene.bubbles_26}")

class ProcessVoxelDataOperator(bpy.types.Operator):
    """Optimized version with three loops for better performance in Blender."""
    bl_idname = "object.process_voxel_data"  # Unique identifier for this operator in Blender
    bl_label = "Process Voxel Data"  # Display name in Blender's UI

    def execute(self, context):
        """
        Main execution method for processing voxel data into a 3D mesh in Blender.

        Parameters:
            context: Blender context object providing access to scene properties

        Returns:
            dict: Operator status ('FINISHED' for success, 'CANCELLED' for failure)
        """
        # Record the start time to measure execution duration
        start_time = time.time()

        # Retrieve file path and dimensions from Blender scene properties
        filepath = context.scene.voxel_file_path  # Path to the voxel data file
        if context.scene.synchronize_dimensions:
            # If dimensions are synchronized, use a uniform size for depth, height, width
            height = width = depth = int(context.scene.voxel_uniform_size)
        else:
            # Otherwise, use individual dimensions from scene properties
            depth = int(context.scene.voxel_depth)    # Number of voxels along depth (x-axis)
            height = int(context.scene.voxel_height)  # Number of voxels along height (y-axis)
            width = int(context.scene.voxel_width)    # Number of voxels along width (z-axis)

        # Get RGB color values from scene properties (assumed to be in 0-255 range)
        red_color = int(context.scene.red_color)    # Red component of material color
        green_color = int(context.scene.green_color)  # Green component
        blue_color = int(context.scene.blue_color)    # Blue component

        # Validate file path; cancel if not provided
        if not filepath:
            self.report({'ERROR'}, "No file path provided.")  # Report error to Blender UI
            return {'CANCELLED'}  # Exit operator with failure status

        try:
            # Clear the current Blender scene by selecting and deleting all objects
            bpy.ops.object.select_all(action="SELECT")  # Select all objects
            bpy.ops.object.delete()  # Delete selected objects

            # Load voxel data efficiently using NumPy
            if filepath.endswith('.npy'):
                data = np.load(filepath)  # Efficient binary format
            else:
                with open(filepath, "r") as file:
                    data = np.loadtxt(file, delimiter=',', dtype=np.uint8)

            # Reshape and rotate the data for correct 3D orientation
            data = data.reshape((depth, height, width))  # Convert flat array to 3D grid
            # Rotate 90 degrees counterclockwise in the height-width plane (y-z plane)
            data = np.rot90(data, k=1, axes=(1, 2))

            # Get the shape of the reshaped data and compute padded dimensions
            shape = data.shape  # Tuple: (depth, height, width)
            padded_shape = (shape[0] + 2, shape[1] + 2, shape[2] + 2)  # Add 2 to each dimension for padding

            # Create a zero-padded array to simplify neighbor calculations
            padded_data = np.zeros(padded_shape, dtype=np.uint8)  # Initialize with zeros
            # Insert original data into the center of the padded array
            padded_data[1:-1, 1:-1, 1:-1] = data

            # Compute the sum of 6-connected neighbors using array slicing
            # Slicing avoids the overhead of np.roll by accessing adjacent layers directly
            neighbor_sum = (
                padded_data[:-2, 1:-1, 1:-1] + padded_data[2:, 1:-1, 1:-1] +  # Top and bottom neighbors
                padded_data[1:-1, :-2, 1:-1] + padded_data[1:-1, 2:, 1:-1] +  # Left and right neighbors
                padded_data[1:-1, 1:-1, :-2] + padded_data[1:-1, 1:-1, 2:]    # Front and back neighbors
            )

            # Identify surface voxels: occupied (1) with fewer than 6 occupied neighbors
            surface_voxels = (data == 1) & (neighbor_sum < 6)

            # Initialize data structures for mesh construction
            vertices = []  # List to store unique vertex coordinates (x, y, z)
            faces = []     # List to store face definitions (quads as vertex index tuples)
            vertex_map = {}  # Dictionary to map vertex coordinates to indices
            face_count = {}  # Dictionary to track face occurrences for deduplication
            cube_size = 1.0  # Size of each voxel cube in Blender units
            
            '''# Get surface voxel indices
            surface_indices = np.where(surface_voxels)
            surface_i, surface_j, surface_k = surface_indices

            # Process only surface voxels
            for i, j, k in zip(surface_i, surface_j, surface_k):'''
              
            # Process each voxel in the 3D grid using three nested loops
            for i in range(surface_voxels.shape[0]):  # Loop over depth (x)
                for j in range(surface_voxels.shape[1]):  # Loop over height (y)
                    for k in range(surface_voxels.shape[2]):  # Loop over width (z)
                        if surface_voxels[i, j, k]:  # If this is a surface voxel
                            # Determine face orientation based on parity of coordinates
                            is_clockwise = (i + j + k) % 2 == 0  # True for clockwise, False for counterclockwise

                            # Define the 8 vertices of a cube at this voxel position
                            cube_vertices = [
                                (i, j, k),                    # Bottom-front-left
                                (i + cube_size, j, k),        # Bottom-front-right
                                (i + cube_size, j + cube_size, k),  # Bottom-back-right
                                (i, j + cube_size, k),        # Bottom-back-left
                                (i, j, k + cube_size),        # Top-front-left
                                (i + cube_size, j, k + cube_size),  # Top-front-right
                                (i + cube_size, j + cube_size, k + cube_size),  # Top-back-right
                                (i, j + cube_size, k + cube_size)  # Top-back-left
                            ]

                            # Assign unique indices to vertices, avoiding duplicates
                            vertex_indices = []
                            for v in cube_vertices:
                                if v not in vertex_map:
                                    # New vertex: assign next index and store coordinates
                                    vertex_map[v] = len(vertices)
                                    vertices.append(v)
                                vertex_indices.append(vertex_map[v])  # Add index to current cube

                            # Define the 6 faces of the cube (quadrilaterals)
                            if is_clockwise:
                                cube_faces = [
                                    (vertex_indices[0], vertex_indices[1], vertex_indices[2], vertex_indices[3]),  # Base
                                    (vertex_indices[4], vertex_indices[5], vertex_indices[6], vertex_indices[7]),  # Top
                                    (vertex_indices[0], vertex_indices[1], vertex_indices[5], vertex_indices[4]),  # Front
                                    (vertex_indices[1], vertex_indices[2], vertex_indices[6], vertex_indices[5]),  # Right
                                    (vertex_indices[2], vertex_indices[3], vertex_indices[7], vertex_indices[6]),  # Back
                                    (vertex_indices[3], vertex_indices[0], vertex_indices[4], vertex_indices[7]),  # Left
                                ]
                            else:
                                # Reverse order for counterclockwise orientation
                                cube_faces = [
                                    (vertex_indices[1], vertex_indices[0], vertex_indices[3], vertex_indices[2]),  # Base
                                    (vertex_indices[5], vertex_indices[4], vertex_indices[7], vertex_indices[6]),  # Top
                                    (vertex_indices[1], vertex_indices[0], vertex_indices[4], vertex_indices[5]),  # Front
                                    (vertex_indices[2], vertex_indices[1], vertex_indices[5], vertex_indices[6]),  # Right
                                    (vertex_indices[3], vertex_indices[2], vertex_indices[6], vertex_indices[7]),  # Back
                                    (vertex_indices[0], vertex_indices[3], vertex_indices[7], vertex_indices[4]),  # Left
                                ]

                            # Track face occurrences to identify internal vs. external faces
                            for face in cube_faces:
                                if face in face_count:
                                    face_count[face] += 1  # Increment count if face already exists
                                else:
                                    face_count[face] = 1  # Initialize count for new face

            # Filter out internal faces (those appearing more than once)
            faces_list = [face for face, count in face_count.items() if count == 1]

            # Create a new Blender mesh from the processed data
            mesh = bpy.data.meshes.new("PerimeterCubesMesh")  # Create mesh object
            mesh.from_pydata(vertices, [], faces_list)  # Populate with vertices and faces (no edges)
            obj = bpy.data.objects.new("PerimeterCubes", mesh)  # Create object from mesh
            bpy.context.collection.objects.link(obj)  # Add object to current scene collection

            # Calculate and report execution time
            execution_time = time.time() - start_time
            self.report({'INFO'}, f"Execution time: {execution_time:.4f} seconds")  # Display in Blender UI

            # Apply a material with the specified color to the object
            color_material = bpy.data.materials.new(name="ColorMaterial")  # Create new material
            # Set diffuse color (normalized to 0-1 range assumed; adjust if input is 0-255)
            color_material.diffuse_color = (red_color, green_color, blue_color, 1.0)
            obj.data.materials.append(color_material)  # Assign material to object

            # Add a camera
            camera_data = bpy.data.cameras.new("Camera")
            camera_object = bpy.data.objects.new("Camera", camera_data)
            bpy.context.collection.objects.link(camera_object)
            camera_object.location = (300, -100, 200)
            obj_center = obj.location
            camera_object.rotation_mode = 'XYZ'
            camera_direction = obj_center - camera_object.location
            camera_object.rotation_euler = camera_direction.to_track_quat('-Z', 'Y').to_euler()
            bpy.context.scene.camera = camera_object

            # Export the mesh to an OBJ file
            output_path = r"C:\Users\Slaye\OneDrive\Escritorio\Test.obj"  # Hardcoded export path
            bpy.ops.wm.obj_export(filepath=output_path)  # Export operation
            
            # Obtener el tamaño del archivo .obj
            if os.path.exists(output_path):  # Verificar que el archivo existe antes de medir su tamaño
                obj_size_bytes = os.path.getsize(output_path)
                obj_size_kb = obj_size_bytes / 1024  # Convertir a KB
                obj_size_mb = obj_size_kb / 1024  # Convertir a MB

                # Reportar el tamaño del archivo .obj en Blender
                self.report({'INFO'}, f"Tamaño del archivo .obj: {obj_size_bytes} bytes ({obj_size_kb:.2f} KB / {obj_size_mb:.2f} MB)")
            else:
                self.report({'ERROR'}, "Error: El archivo .obj no se generó correctamente.")
                
            # Report successful completion
            self.report({'INFO'}, "Voxel data processed and object created successfully!")

        except Exception as e:
            # Handle any errors during execution (e.g., file not found, invalid data)
            self.report({'ERROR'}, f"Failed to process file: {e}")
            return {'CANCELLED'}  # Exit with failure status

        return {'FINISHED'}  # Successful completion status


class ProcessVoxelDataOperatorComplete(bpy.types.Operator):
    """
    Reads and processes voxel data from a file, creates a 3D representation of the perimeter voxels,
    and adds it to the Blender scene. The operator clears the current scene, processes the voxel data,
    generates 3D geometry for perimeter voxels, and sets up a camera and material for the created object.

    Attributes:
        bl_idnameC (str): Unique identifier for the operator.
        bl_labelC (str): Display label for the operator in the Blender UI.

    Methods:
        execute(context):
            Main execution method for the operator. Reads voxel data, processes it, generates a 3D model,
            applies material and color, and sets up a camera. Returns operation status.
    """
    
    bl_idname = "object.process_voxel_data_complete"
    bl_label = "Process Voxel Data Complete"
    
    def execute(self, context):
        # Get the file path and dimensions from the scene
        
        start_time = time.time()  # Record the start time
        
        filepath = context.scene.voxel_file_path
        
        # Check if dimensions are synchronized
        if context.scene.synchronize_dimensions:
            height = width = depth = int(context.scene.voxel_uniform_size)
        else:
            depth = int(context.scene.voxel_depth)
            height = int(context.scene.voxel_height)
            width = int(context.scene.voxel_width)
        
        Red_color = int(context.scene.red_color)
        Green_color = int(context.scene.green_color)
        Blue_color = int(context.scene.blue_color)
            
        # Ensure a file path is provided
        if not filepath:
            self.report({'ERROR'}, "No file path provided.")
            return {'CANCELLED'}
        
        try:
            # Clear the scene
            bpy.ops.object.select_all(action="SELECT")
            bpy.ops.object.delete()

            # Open and read the file
            with open(filepath, "r") as file:
                data = np.loadtxt(file, delimiter=',')
            
            # Reshape and process the data
            data = data.reshape(depth, height, width)
            data = np.rot90(data, k=1, axes=(1, 2))
            
            # Define the size of each cube (voxel) in the 3D model
            Cube_size = 1.0  # You can adjust this value as needed

            padded_data = np.pad(data, 1, mode='constant')
            
            neighbor_sum = (
                np.roll(padded_data, 1, axis=0) + np.roll(padded_data, -1, axis=0)
                + np.roll(padded_data, 1, axis=1) + np.roll(padded_data, -1, axis=1)
                + np.roll(padded_data, 1, axis=2) + np.roll(padded_data, -1, axis=2)
            )
            
            perimeter_voxels = (data == 1) & (neighbor_sum[1:-1, 1:-1, 1:-1] < 6)
            
            # Create the 3D geometry
            vertices, edges, faces = [], [], []
            
            for i in range(perimeter_voxels.shape[0]):
                for j in range(perimeter_voxels.shape[1]):
                    for k in range(perimeter_voxels.shape[2]):
                        if perimeter_voxels[i, j, k]:
                          
                            cube_vertices = [
                                (i, j, k), (i + Cube_size, j, k), (i + Cube_size, j + Cube_size, k), (i, j + Cube_size, k),
                                (i, j, k + Cube_size), (i + Cube_size, j, k + Cube_size), (i + Cube_size, j + Cube_size, k + Cube_size), (i, j + Cube_size, k + Cube_size)
                            ]
                            
                            vertices.extend(cube_vertices)
                            start_index = len(vertices) - 8
                            
                            faces.extend([
                                (start_index, start_index + 1, start_index + 2, start_index + 3),
                                (start_index + 4, start_index + 5, start_index + 6, start_index + 7),
                                (start_index, start_index + 1, start_index + 5, start_index + 4),
                                (start_index + 1, start_index + 2, start_index + 6, start_index + 5),
                                (start_index + 2, start_index + 3, start_index + 7, start_index + 6),
                                (start_index + 3, start_index, start_index + 4, start_index + 7)
                            ])
            
            # Create the mesh and object
            mesh = bpy.data.meshes.new("PerimeterCubesMesh")
            mesh.from_pydata(vertices, edges, faces)
            obj = bpy.data.objects.new("PerimeterCubes", mesh)
            bpy.context.collection.objects.link(obj)
            
            # Seleccionar el objeto recién creado
            bpy.ops.object.select_all(action='DESELECT')  # Deseleccionar todo
            obj.select_set(True)  # Seleccionar el objeto
            bpy.context.view_layer.objects.active = obj  # Establecer como objeto activo
            
            # Add a color material
            Color_material = bpy.data.materials.new(name="ColorMaterial")
            Color_material.diffuse_color = (Red_color, Green_color, Blue_color, 1.0)  # RGBA: Red with full opacity
            obj.data.materials.append(Color_material)
            
            end_time = time.time()  # Record the end time
            execution_time = end_time - start_time  # Calculate the total execution time

            # Display the execution time in Blender's interface
            self.report({'INFO'}, f"Execution time: {execution_time:.4f} seconds")
        
            # Add a camera
            camera_data = bpy.data.cameras.new("Camera")
            camera_object = bpy.data.objects.new("Camera", camera_data)
            bpy.context.collection.objects.link(camera_object)
            camera_object.location = (300, -100, 200)
            obj_center = obj.location
            camera_object.rotation_mode = 'XYZ'
            camera_direction = obj_center - camera_object.location
            camera_object.rotation_euler = camera_direction.to_track_quat('-Z', 'Y').to_euler()
            bpy.context.scene.camera = camera_object
            
            # Exportar el objeto a un archivo .obj
            output_path = r"C:\Users\Slaye\OneDrive\Escritorio\Test_1.obj"  # Cambia esto por la ruta deseada
            bpy.ops.wm.obj_export(filepath=output_path)
            
            # Obtener el tamaño del archivo .obj
            if os.path.exists(output_path):  # Verificar que el archivo existe antes de medir su tamaño
                obj_size_bytes = os.path.getsize(output_path)
                obj_size_kb = obj_size_bytes / 1024  # Convertir a KB
                obj_size_mb = obj_size_kb / 1024  # Convertir a MB

                # Reportar el tamaño del archivo .obj en Blender
                self.report({'INFO'}, f"Tamaño del archivo .obj: {obj_size_bytes} bytes ({obj_size_kb:.2f} KB / {obj_size_mb:.2f} MB)")
            else:
                self.report({'ERROR'}, "Error: El archivo .obj no se generó correctamente.")
                
            # Success message
            self.report({'INFO'}, "Voxel data processed and object created successfully!")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to process file: {e}")
            return {'CANCELLED'}
    
        return {'FINISHED'}
      
class BaseCountConnectedComponentsOperator(bpy.types.Operator):
    """Base operator for counting connected components in voxel data."""
    # Precomputed neighbor lists as class attributes
    NEIGHBORS_6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    NEIGHBORS_18 = [(x, y, z) for x in [-1, 0, 1] for y in [-1, 0, 1] for z in [-1, 0, 1]
                    if (x, y, z) != (0, 0, 0) and abs(x) + abs(y) + abs(z) <= 2]
    NEIGHBORS_26 = [(x, y, z) for x in [-1, 0, 1] for y in [-1, 0, 1] for z in [-1, 0, 1]
                    if (x, y, z) != (0, 0, 0)]

    def get_voxel_data(self, context):
        """Read and reshape voxel data from the file based on scene properties."""
        filepath = context.scene.voxel_file_path

        # Determine dimensions from scene properties
        if context.scene.synchronize_dimensions:
            height = width = depth = int(context.scene.voxel_uniform_size)
        else:
            depth = int(context.scene.voxel_depth)
            height = int(context.scene.voxel_height)
            width = int(context.scene.voxel_width)

        # Validate file path
        if not filepath:
            self.report({'ERROR'}, "No file path provided.")
            return None

        try:
            with open(filepath, "r") as file:
                data = np.loadtxt(file, delimiter=',')
            data = data.reshape(depth, height, width)
            return data
        except Exception as e:
            self.report({'ERROR'}, f"Error processing file: {e}")
            return None

    @staticmethod
    def find_connected_components(data, connectivity):
        """Compute the number of connected components using the specified connectivity."""
        # Select neighbor list based on connectivity
        if connectivity == 6:
            neighbors = BaseCountConnectedComponentsOperator.NEIGHBORS_6
        elif connectivity == 18:
            neighbors = BaseCountConnectedComponentsOperator.NEIGHBORS_18
        elif connectivity == 26:
            neighbors = BaseCountConnectedComponentsOperator.NEIGHBORS_26
        else:
            raise ValueError("Invalid connectivity: must be 6, 18, or 26.")

        # Get dimensions and initialize visited array
        shape_x, shape_y, shape_z = data.shape
        total_voxels = shape_x * shape_y * shape_z
        visited = np.zeros(total_voxels, dtype=bool)
        components = 0

        def bfs(start_idx):
            """Perform BFS to explore a connected component."""
            queue = deque([start_idx])
            visited[start_idx] = True
            while queue:
                current_idx = queue.popleft()
                cx = current_idx // (shape_y * shape_z)
                cy = (current_idx % (shape_y * shape_z)) // shape_z
                cz = current_idx % shape_z
                for dx, dy, dz in neighbors:
                    nx, ny, nz = cx + dx, cy + dy, cz + dz
                    if 0 <= nx < shape_x and 0 <= ny < shape_y and 0 <= nz < shape_z:
                        neighbor_idx = nx * shape_y * shape_z + ny * shape_z + nz
                        if data[nx, ny, nz] == 1 and not visited[neighbor_idx]:
                            visited[neighbor_idx] = True
                            queue.append(neighbor_idx)

        # Iterate over all voxels to find components
        for idx in range(total_voxels):
            if data.flat[idx] == 1 and not visited[idx]:
                components += 1
                bfs(idx)

        return components

class CountConnectedComponents6Operator(BaseCountConnectedComponentsOperator):
    """Counts connected components using 6-connectivity."""
    bl_idname = "object.count_connected_components_6"
    bl_label = "Count Connected Components (6-connectivity)"

    def execute(self, context):
        """Execute the operator for 6-connectivity."""
        data = self.get_voxel_data(context)
        if data is None:
            return {'CANCELLED'}

        start_time = time.time()
        components = BaseCountConnectedComponentsOperator.find_connected_components(data, 6)
        exec_time = time.time() - start_time

        context.scene.components_6 = components
        self.report({'INFO'}, f"Connected components (6-connectivity): {components}, "
                              f"Execution time: {exec_time:.4f} seconds")
        return {'FINISHED'}
      
class CountConnectedComponents18Operator(BaseCountConnectedComponentsOperator):
    """Counts connected components using 18-connectivity."""
    bl_idname = "object.count_connected_components_18"
    bl_label = "Count Connected Components (18-connectivity)"

    def execute(self, context):
        """Execute the operator for 18-connectivity."""
        data = self.get_voxel_data(context)
        if data is None:
            return {'CANCELLED'}

        start_time = time.time()
        components = BaseCountConnectedComponentsOperator.find_connected_components(data, 18)
        exec_time = time.time() - start_time

        context.scene.components_18 = components
        self.report({'INFO'}, f"Connected components (18-connectivity): {components}, "
                              f"Execution time: {exec_time:.4f} seconds")
        return {'FINISHED'}

class CountConnectedComponents26Operator(BaseCountConnectedComponentsOperator):
    """Counts connected components using 26-connectivity."""
    bl_idname = "object.count_connected_components_26"
    bl_label = "Count Connected Components (26-connectivity)"

    def execute(self, context):
        """Execute the operator for 26-connectivity."""
        data = self.get_voxel_data(context)
        if data is None:
            return {'CANCELLED'}

        start_time = time.time()
        components = BaseCountConnectedComponentsOperator.find_connected_components(data, 26)
        exec_time = time.time() - start_time

        context.scene.components_26 = components
        self.report({'INFO'}, f"Connected components (26-connectivity): {components}, "
                              f"Execution time: {exec_time:.4f} seconds")
        return {'FINISHED'}
      
class BaseCountBubblesOperator(bpy.types.Operator):
    """Base operator for counting bubbles in voxel data."""
    # Precomputed neighbor lists as class attributes
    NEIGHBORS_6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    NEIGHBORS_18 = [(x, y, z) for x in [-1, 0, 1] for y in [-1, 0, 1] for z in [-1, 0, 1]
                    if (x, y, z) != (0, 0, 0) and abs(x) + abs(y) + abs(z) <= 2]
    NEIGHBORS_26 = [(x, y, z) for x in [-1, 0, 1] for y in [-1, 0, 1] for z in [-1, 0, 1]
                    if (x, y, z) != (0, 0, 0)]

    def get_voxel_data(self, context):
        """Read and reshape voxel data from the file based on scene properties."""
        filepath = context.scene.voxel_file_path

        # Determine dimensions from scene properties
        if context.scene.synchronize_dimensions:
            height = width = depth = int(context.scene.voxel_uniform_size)
        else:
            depth = int(context.scene.voxel_depth)
            height = int(context.scene.voxel_height)
            width = int(context.scene.voxel_width)

        # Validate file path
        if not filepath:
            self.report({'ERROR'}, "No file path provided.")
            return None

        try:
            with open(filepath, "r") as file:
                data = np.loadtxt(file, delimiter=',')
            data = data.reshape(depth, height, width)
            return data
        except Exception as e:
            self.report({'ERROR'}, f"Error processing file: {e}")
            return None

    @staticmethod
    def find_bubbles(data, connectivity):
        """
        Identifies and counts enclosed air pockets (bubbles) in 3D voxel data.

        Parameters:
            data (np.ndarray): 3D array of binary voxel data (0 = empty, 1 = occupied)
            connectivity (int): Type of voxel connectivity (6, 18, or 26)

        Returns:
            int: Number of fully enclosed air pockets (bubbles)
        """
        # Select neighbor list based on connectivity
        if connectivity == 6:
            neighbors = BaseCountBubblesOperator.NEIGHBORS_6
        elif connectivity == 18:
            neighbors = BaseCountBubblesOperator.NEIGHBORS_18
        elif connectivity == 26:
            neighbors = BaseCountBubblesOperator.NEIGHBORS_26
        else:
            raise ValueError("Invalid connectivity: must be 6, 18, or 26.")

        # Get dimensions
        shape_x, shape_y, shape_z = data.shape
        visited = np.zeros_like(data, dtype=bool)

        def bfs(start_x, start_y, start_z):
            """Performs BFS to explore a connected component of empty voxels."""
            queue = deque([(start_x, start_y, start_z)])
            visited[start_x, start_y, start_z] = True
            is_boundary = False
            while queue:
                cx, cy, cz = queue.popleft()
                for dx, dy, dz in neighbors:
                    nx, ny, nz = cx + dx, cy + dy, cz + dz
                    if 0 <= nx < shape_x and 0 <= ny < shape_y and 0 <= nz < shape_z:
                        if data[nx, ny, nz] == 0 and not visited[nx, ny, nz]:
                            visited[nx, ny, nz] = True
                            queue.append((nx, ny, nz))
                    else:
                        is_boundary = True
            return not is_boundary

        bubbles = 0
        for x, y, z in zip(*np.nonzero(data == 0)):
            if not visited[x, y, z]:
                if bfs(x, y, z):
                    bubbles += 1
        return max(0, bubbles)

class CountBubbles6Operator(BaseCountBubblesOperator):
    """Counts bubbles using 6-connectivity."""
    bl_idname = "object.count_bubbles_6"
    bl_label = "Count Bubbles (6-connectivity)"

    def execute(self, context):
        """Execute the operator for 6-connectivity."""
        data = self.get_voxel_data(context)
        if data is None:
            return {'CANCELLED'}

        start_time = time.time()
        bubbles = BaseCountBubblesOperator.find_bubbles(data, 6)
        exec_time = time.time() - start_time

        context.scene.bubbles_6 = bubbles
        self.report({'INFO'}, f"Bubbles (6-connectivity): {bubbles}, Execution time: {exec_time:.4f} seconds")
        return {'FINISHED'}

class CountBubbles18Operator(BaseCountBubblesOperator):
    """Counts bubbles using 18-connectivity."""
    bl_idname = "object.count_bubbles_18"
    bl_label = "Count Bubbles (18-connectivity)"

    def execute(self, context):
        """Execute the operator for 18-connectivity."""
        data = self.get_voxel_data(context)
        if data is None:
            return {'CANCELLED'}

        start_time = time.time()
        bubbles = BaseCountBubblesOperator.find_bubbles(data, 18)
        exec_time = time.time() - start_time

        context.scene.bubbles_18 = bubbles
        self.report({'INFO'}, f"Bubbles (18-connectivity): {bubbles}, Execution time: {exec_time:.4f} seconds")
        return {'FINISHED'}

class CountBubbles26Operator(BaseCountBubblesOperator):
    """Counts bubbles using 26-connectivity."""
    bl_idname = "object.count_bubbles_26"
    bl_label = "Count Bubbles (26-connectivity)"

    def execute(self, context):
        """Execute the operator for 26-connectivity."""
        data = self.get_voxel_data(context)
        if data is None:
            return {'CANCELLED'}

        start_time = time.time()
        bubbles = BaseCountBubblesOperator.find_bubbles(data, 26)
        exec_time = time.time() - start_time

        context.scene.bubbles_26 = bubbles
        self.report({'INFO'}, f"Bubbles (26-connectivity): {bubbles}, Execution time: {exec_time:.4f} seconds")
        return {'FINISHED'}
      
def register():
    # Register properties for the scene. These properties allow the user to configure the voxel settings
    # in the Blender interface.

    # Property to store the file path to the voxel data file
    bpy.types.Scene.voxel_file_path = bpy.props.StringProperty(
        name="Voxel File Path",
        description="Path to the voxel data file",
        default="",
        subtype='FILE_PATH'
    )
    
    # Boolean property to indicate if height, width, and depth should be synchronized (same value)
    bpy.types.Scene.synchronize_dimensions = bpy.props.BoolProperty(
        name="Synchronize Dimensions",
        description="Use the same value for height, width, and depth",
        default=False
    )
    
    # Float property for uniform size of the voxel grid (applied when synchronization is enabled)
    bpy.types.Scene.voxel_uniform_size = bpy.props.FloatProperty(
        name="Uniform Size",
        description="Size for height, width, and depth when synchronized",
        default=64.0
    )
    
    # Individual properties for the depth, height, and width of the voxel grid
    bpy.types.Scene.voxel_depth = bpy.props.FloatProperty(
        name="Depth",
        description="Depth of the voxel grid",
        default=64.0
    )
    bpy.types.Scene.voxel_height = bpy.props.FloatProperty(
        name="Height",
        description="Height of the voxel grid",
        default=64.0
    )
    bpy.types.Scene.voxel_width = bpy.props.FloatProperty(
        name="Width",
        description="Width of the voxel grid",
        default=64.0
    )
    
    # Float properties to define the RGB color values for the voxels
    bpy.types.Scene.red_color = bpy.props.FloatProperty(
        name="R",
        description="Red color",
        default=1.0
    )
    bpy.types.Scene.green_color = bpy.props.FloatProperty(
        name="G",
        description="Green color",
        default=1.0
    )
    bpy.types.Scene.blue_color = bpy.props.FloatProperty(
        name="B",
        description="Blue color",
        default=1.0
    )
    
    # Property to store results related to connected components in the voxel data
    bpy.types.Scene.connectivity_results = bpy.props.StringProperty(
        name="Connectivity Results",
        description="Stores results of connected components",
        default=""
    )
    
    # Property to store results related to bubbles in the voxel data
    bpy.types.Scene.bubble_results = bpy.props.StringProperty(
        name="Bubble Results",
        description="Stores results of Bubbles",
        default=""
    )
    
    bpy.types.Scene.components_6 = bpy.props.IntProperty(name="Components 6", default=0)
    bpy.types.Scene.components_18 = bpy.props.IntProperty(name="Components 18", default=0)
    bpy.types.Scene.components_26 = bpy.props.IntProperty(name="Components 26", default=0)

    bpy.types.Scene.bubbles_6 = bpy.props.IntProperty(name="Bubbles 6", default=0)
    bpy.types.Scene.bubbles_18 = bpy.props.IntProperty(name="Bubbles 18", default=0)
    bpy.types.Scene.bubbles_26 = bpy.props.IntProperty(name="Bubbles 26", default=0)
    
    # Register the custom classes to make them available in Blender
    bpy.utils.register_class(VoxelProcessingPanel)  # Custom UI panel for voxel processing
    bpy.utils.register_class(ProcessVoxelDataOperator)  # Operator for processing voxel data
    bpy.utils.register_class(ProcessVoxelDataOperatorComplete)  # Operator for processing voxel data
    bpy.utils.register_class(CountConnectedComponents6Operator)  # Operator to count connected components with 6-connectivity
    bpy.utils.register_class(CountConnectedComponents18Operator)  # Operator to count connected components with 18-connectivity
    bpy.utils.register_class(CountConnectedComponents26Operator)  # Operator to count connected components with 26-connectivity
    bpy.utils.register_class(CountBubbles6Operator)  # Operator to count bubbles with 6-connectivity
    bpy.utils.register_class(CountBubbles18Operator)  # Operator to count bubbles with 18-connectivity
    bpy.utils.register_class(CountBubbles26Operator)  # Operator to count bubbles with 26-connectivity
    
def unregister():
    # Unregister the custom classes to clean up when the script is disabled
    bpy.utils.unregister_class(VoxelProcessingPanel)
    bpy.utils.unregister_class(ProcessVoxelDataOperator)
    bpy.utils.unregister_class(ProcessVoxelDataOperatorComplete)
    bpy.utils.unregister_class(CountConnectedComponents6Operator)
    bpy.utils.unregister_class(CountConnectedComponents18Operator)
    bpy.utils.unregister_class(CountConnectedComponents26Operator)
    bpy.utils.unregister_class(CountBubbles6Operator)
    bpy.utils.unregister_class(CountBubbles18Operator)
    bpy.utils.unregister_class(CountBubbles26Operator)
    
    # Remove the registered properties from the scene to free up resources
    del bpy.types.Scene.voxel_file_path
    del bpy.types.Scene.synchronize_dimensions
    del bpy.types.Scene.voxel_uniform_size
    
    del bpy.types.Scene.voxel_depth
    del bpy.types.Scene.voxel_height
    del bpy.types.Scene.voxel_width
    
    del bpy.types.Scene.red_color
    del bpy.types.Scene.green_color
    del bpy.types.Scene.blue_color
    
    del bpy.types.Scene.connectivity_results
    del bpy.types.Scene.bubble_results
    
    del bpy.types.Scene.components_6
    del bpy.types.Scene.components_18
    del bpy.types.Scene.components_26
    del bpy.types.Scene.bubbles_6
    del bpy.types.Scene.bubbles_18
    del bpy.types.Scene.bubbles_26
    

# Main entry point: Registers the properties and classes when the script is run
if __name__ == "__main__":
    register()