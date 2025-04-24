#!/usr/bin/env python3

"""
Physical Mapper Module
---------------------
Handles the mapping between monitors based on physical dimensions and trajectory vectors.
Implements both direct correspondence mapping and trajectory-based mapping for zones
where there's no direct physical overlap.
"""

import logging
import math
from monitor import Monitor


class PhysicalMapper:
    """Maps cursor positions between monitors using physical coordinates."""
    
    def __init__(self, config, logger=None):
        """
        Initialize the physical mapper with monitor configurations.
        
        Args:
            config: Configuration dictionary from config.json
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config = config
        
        # Get monitor names from config
        self.top_monitor_name = config["top_monitor"]
        self.bottom_monitor_name = config["bottom_monitor"]
        
        # Create monitor objects
        self.monitors = {}
        for monitor_data in config["monitors"]:
            name = monitor_data["name"]
            self.monitors[name] = Monitor(monitor_data, logger)
        
        # Get top and bottom monitor references
        self.top_monitor = self.monitors[self.top_monitor_name]
        self.bottom_monitor = self.monitors[self.bottom_monitor_name]
        
        # Calculate mapping zones
        self._calculate_mapping_zones()
        
        # Initialize trajectory tracking
        self.trajectory_padding_distance = 5  # mm, distance from border to start tracking trajectory
        self.reset_trajectory_tracking()
    
    def _calculate_mapping_zones(self):
        """Calculate the direct correspondence and trajectory zones for monitors."""
        # Calculate physical positions of monitors
        top_extents = self.top_monitor.get_physical_extents()
        bottom_extents = self.bottom_monitor.get_physical_extents()
        
        # Get physical dimensions
        top_width_mm = top_extents["width_mm"]
        bottom_width_mm = bottom_extents["width_mm"]
        
        self.logger.info(f"Top monitor physical width: {top_width_mm}mm")
        self.logger.info(f"Bottom monitor physical width: {bottom_width_mm}mm")
        
        # Important: In physical space, the physically wider monitor should be the reference
        # regardless of pixel coordinates. We'll use top-left corner of the physically wider
        # monitor as (0,0) in physical space.
        
        # Determine which monitor is physically wider
        wider_is_top = top_width_mm >= bottom_width_mm
        
        # Pixel offsets from config
        top_x_offset_px = self.top_monitor.x_offset_px
        bottom_x_offset_px = self.bottom_monitor.x_offset_px
        
        self.logger.info(f"Top monitor x offset: {top_x_offset_px}px")
        self.logger.info(f"Bottom monitor x offset: {bottom_x_offset_px}px")
        
        # Calculate physical coordinate of each monitor's left edge
        # We need to determine the physical offset between monitors
        if wider_is_top:
            # Top monitor is physically wider, set its left edge as physical 0
            self.top_left_mm = 0
            self.top_right_mm = top_width_mm
            
            # Calculate bottom monitor's physical position relative to top
            # Need to center the narrower monitor horizontally relative to the wider one
            phys_offset_mm = (top_width_mm - bottom_width_mm) / 2
            self.bottom_left_mm = phys_offset_mm
            self.bottom_right_mm = phys_offset_mm + bottom_width_mm
            
            self.logger.info(f"Top monitor (wider) is reference point in physical space")
        else:
            # Bottom monitor is physically wider, set its left edge as physical 0
            self.bottom_left_mm = 0
            self.bottom_right_mm = bottom_width_mm
            
            # Calculate top monitor's physical position relative to bottom
            phys_offset_mm = (bottom_width_mm - top_width_mm) / 2
            self.top_left_mm = phys_offset_mm
            self.top_right_mm = phys_offset_mm + top_width_mm
            
            self.logger.info(f"Bottom monitor (wider) is reference point in physical space")
        
        # Calculate overlap for direct mapping zones
        self.overlap_left_mm = max(self.bottom_left_mm, self.top_left_mm)
        self.overlap_right_mm = min(self.bottom_right_mm, self.top_right_mm)
        self.has_direct_overlap = self.overlap_left_mm < self.overlap_right_mm
        
        # Store Y coordinates for monitors in physical space
        self.top_monitor_height_mm = self.top_monitor.height_mm
        self.bottom_monitor_height_mm = self.bottom_monitor.height_mm
        
        # Define the Y coordinates of monitor edges in global physical space
        # Top monitor is at Y=0, bottom monitor is below it
        self.top_top_edge_y_mm = 0
        self.top_bottom_edge_y_mm = self.top_monitor_height_mm
        self.bottom_top_edge_y_mm = self.top_monitor_height_mm  # Bottom monitor starts right after top
        self.bottom_bottom_edge_y_mm = self.top_monitor_height_mm + self.bottom_monitor_height_mm
        
        # Identify mapping zones with full 2D coordinates
        if self.has_direct_overlap:
            # Direct mapping zone where monitors physically overlap (horizontal)
            self.logger.info(f"Direct mapping zone in 2D space:")
            self.logger.info(f"  Top monitor: ({self.overlap_left_mm:.1f}mm, {self.top_bottom_edge_y_mm:.1f}mm) to ({self.overlap_right_mm:.1f}mm, {self.top_bottom_edge_y_mm:.1f}mm)")
            self.logger.info(f"  Bottom monitor: ({self.overlap_left_mm:.1f}mm, {self.bottom_top_edge_y_mm:.1f}mm) to ({self.overlap_right_mm:.1f}mm, {self.bottom_top_edge_y_mm:.1f}mm)")
            
            # Left trajectory zone - left edge of top monitor connects to left edge of bottom monitor
            if self.top_left_mm < self.overlap_left_mm:
                self.logger.info(f"Left trajectory zone:")
                self.logger.info(f"  Top monitor left edge: ({self.top_left_mm:.1f}mm, {self.top_bottom_edge_y_mm:.1f}mm) to ({self.overlap_left_mm:.1f}mm, {self.top_bottom_edge_y_mm:.1f}mm)")
                self.logger.info(f"  Maps to bottom monitor left edge: ({self.bottom_left_mm:.1f}mm, {self.bottom_top_edge_y_mm:.1f}mm) to ({self.bottom_left_mm:.1f}mm, {self.bottom_bottom_edge_y_mm:.1f}mm)")
            
            # Right trajectory zone - right edge of top monitor connects to right edge of bottom monitor
            if self.top_right_mm > self.overlap_right_mm:
                self.logger.info(f"Right trajectory zone:")
                self.logger.info(f"  Top monitor right edge: ({self.overlap_right_mm:.1f}mm, {self.top_bottom_edge_y_mm:.1f}mm) to ({self.top_right_mm:.1f}mm, {self.top_bottom_edge_y_mm:.1f}mm)")
                self.logger.info(f"  Maps to bottom monitor right edge: ({self.bottom_right_mm:.1f}mm, {self.bottom_top_edge_y_mm:.1f}mm) to ({self.bottom_right_mm:.1f}mm, {self.bottom_bottom_edge_y_mm:.1f}mm)")
        else:
            self.logger.warning("No direct overlap between monitors")
        
        # Define trajectory zones with full 2D coordinates
        # Store as tuples of (x_start, y_start, x_end, y_end) in mm
        
        # Bottom left trajectory zone (left side of bottom monitor to bottom of top monitor)
        if self.bottom_left_mm < self.overlap_left_mm:
            self.bottom_left_trajectory = {
                # Source is the left side of bottom monitor (full height)
                'source': (self.bottom_left_mm, self.bottom_top_edge_y_mm, self.bottom_left_mm, self.bottom_bottom_edge_y_mm),
                # Target is the bottom edge of top monitor (from left)
                'target': (self.top_left_mm, self.top_bottom_edge_y_mm, self.overlap_left_mm, self.top_bottom_edge_y_mm)
            }
            self.logger.info(f"Bottom left trajectory zone:")
            self.logger.info(f"  Source (full left side of bottom monitor): ({self.bottom_left_mm:.1f}mm, {self.bottom_top_edge_y_mm:.1f}mm) to ({self.bottom_left_mm:.1f}mm, {self.bottom_bottom_edge_y_mm:.1f}mm)")
            self.logger.info(f"  Target (left portion of bottom edge of top): ({self.top_left_mm:.1f}mm, {self.top_bottom_edge_y_mm:.1f}mm) to ({self.overlap_left_mm:.1f}mm, {self.top_bottom_edge_y_mm:.1f}mm)")
        else:
            self.bottom_left_trajectory = None
        
        # Bottom right trajectory zone (right side of bottom monitor to bottom of top monitor)
        if self.bottom_right_mm > self.overlap_right_mm:
            self.bottom_right_trajectory = {
                # Source is the right side of bottom monitor (full height)
                'source': (self.bottom_right_mm, self.bottom_top_edge_y_mm, self.bottom_right_mm, self.bottom_bottom_edge_y_mm),
                # Target is the bottom edge of top monitor (from right)
                'target': (self.overlap_right_mm, self.top_bottom_edge_y_mm, self.top_right_mm, self.top_bottom_edge_y_mm)
            }
            self.logger.info(f"Bottom right trajectory zone:")
            self.logger.info(f"  Source (full right side of bottom monitor): ({self.bottom_right_mm:.1f}mm, {self.bottom_top_edge_y_mm:.1f}mm) to ({self.bottom_right_mm:.1f}mm, {self.bottom_bottom_edge_y_mm:.1f}mm)")
            self.logger.info(f"  Target (right portion of bottom edge of top): ({self.overlap_right_mm:.1f}mm, {self.top_bottom_edge_y_mm:.1f}mm) to ({self.top_right_mm:.1f}mm, {self.top_bottom_edge_y_mm:.1f}mm)")
        else:
            self.bottom_right_trajectory = None
        
        # No top left/right trajectory zones as they should not exist
        self.top_left_trajectory = None
        self.top_right_trajectory = None
    
    def reset_trajectory_tracking(self):
        """Reset trajectory tracking variables."""
        self.in_trajectory_zone = False
        self.trajectory_entry_point = None
        self.current_position = None
    
    def track_position(self, x_px, y_px):
        """
        Track mouse position to determine if we're in a trajectory zone.
        
        Args:
            x_px: Absolute X pixel coordinate
            y_px: Absolute Y pixel coordinate
            
        Returns:
            True if position was tracked, False otherwise
        """
        # Determine which monitor the cursor is on
        on_top = self.top_monitor.is_point_on_monitor(x_px, y_px)
        on_bottom = self.bottom_monitor.is_point_on_monitor(x_px, y_px)
        
        if not (on_top or on_bottom):
            self.reset_trajectory_tracking()
            return False
        
        # Get current monitor
        current_monitor = self.top_monitor if on_top else self.bottom_monitor
        
        # Convert to physical coordinates (relative to the monitor's local space)
        local_physical_pos = current_monitor.pixels_to_world(x_px, y_px)
        local_x_mm, local_y_mm = local_physical_pos
        
        # Convert to global physical space
        # Add the monitor's physical offset to get global coordinates
        if on_top:
            x_mm = self.top_left_mm + local_x_mm
            y_mm = local_y_mm  # Top monitor y starts at 0
        else:  # on bottom
            x_mm = self.bottom_left_mm + local_x_mm
            y_mm = self.top_monitor_height_mm + local_y_mm  # Below top monitor
            
        # Store physical position in global space
        physical_pos = (x_mm, y_mm)
        
        # Store current position
        self.current_position = (x_px, y_px, physical_pos)
        
        # Check if we're near a boundary between monitors
        # For trajectory calculation, we need to know if we're approaching an edge
        if on_top:
            # Near bottom edge of top monitor?
            near_edge = abs(y_mm - self.top_bottom_edge_y_mm) <= self.trajectory_padding_distance
            # Identify which zone we're in horizontally
            if near_edge:
                if x_mm < self.overlap_left_mm:  # Left trajectory zone
                    edge_type = "top_left"
                elif x_mm > self.overlap_right_mm:  # Right trajectory zone
                    edge_type = "top_right"
                else:  # Direct mapping zone
                    edge_type = "top_direct"
            else:
                edge_type = None
                
        else:  # on bottom
            # Near top edge of bottom monitor?
            near_edge = abs(y_mm - self.bottom_top_edge_y_mm) <= self.trajectory_padding_distance
            # Identify which zone we're in horizontally
            if near_edge:
                if x_mm < self.overlap_left_mm:  # Left trajectory zone
                    edge_type = "bottom_left"
                elif x_mm > self.overlap_right_mm:  # Right trajectory zone
                    edge_type = "bottom_right"
                else:  # Direct mapping zone
                    edge_type = "bottom_direct"
            else:
                edge_type = None
        
        # If near a boundary, track for trajectory calculation
        if near_edge:
            # If just entering trajectory zone, record entry point
            if not self.in_trajectory_zone:
                self.in_trajectory_zone = True
                self.trajectory_entry_point = (x_px, y_px, physical_pos, edge_type)
                self.logger.info(f"Entered trajectory zone '{edge_type}' at physical coordinates: ({x_mm:.1f}mm, {y_mm:.1f}mm)")
            return True
        else:
            # If leaving trajectory zone, reset tracking
            if self.in_trajectory_zone:
                self.reset_trajectory_tracking()
            return False
    
    def check_border_crossing(self, prev_y_px, y_px):
        """
        Check if the cursor has crossed the border between monitors.
        
        Args:
            prev_y_px: Previous Y pixel coordinate
            y_px: Current Y pixel coordinate
            
        Returns:
            Direction of crossing ('up', 'down', or None)
        """
        if prev_y_px is None:
            return None
        
        # Get Y coordinates of monitor boundaries
        top_bottom_px = self.top_monitor.y_offset_px + self.top_monitor.height_px
        bottom_top_px = self.bottom_monitor.y_offset_px
        
        # Check if cursor crossed from top to bottom monitor
        if prev_y_px < top_bottom_px and y_px >= top_bottom_px:
            return 'down'
        
        # Check if cursor crossed from bottom to top monitor
        if prev_y_px >= bottom_top_px and y_px < bottom_top_px:
            return 'up'
        
        return None
    
    def calculate_jump_position(self, x_px, y_px, direction):
        """
        Calculate the new cursor position when jumping between monitors.
        
        Args:
            x_px: Absolute X pixel coordinate where border was crossed
            y_px: Absolute Y pixel coordinate where border was crossed
            direction: Direction of crossing ('up' or 'down')
            
        Returns:
            New (x_px, y_px) position after jump, or None if no jump
        """
        self.logger.info(f"Calculating jump from ({x_px}, {y_px}) direction: {direction}")
        
        # Get source and target monitors
        if direction == 'up':  # Bottom to Top
            source_monitor = self.bottom_monitor
            target_monitor = self.top_monitor
            source_edge_y_mm = self.bottom_top_edge_y_mm
            target_edge_y_mm = self.top_bottom_edge_y_mm
        else:  # Top to Bottom
            source_monitor = self.top_monitor
            target_monitor = self.bottom_monitor
            source_edge_y_mm = self.top_bottom_edge_y_mm
            target_edge_y_mm = self.bottom_top_edge_y_mm
        
        # Convert crossing point to local physical coordinates
        local_physical_pos = source_monitor.pixels_to_world(x_px, y_px)
        local_x_mm, local_y_mm = local_physical_pos
        
        # Convert to global physical space
        if direction == 'up':  # Bottom to Top
            x_mm = self.bottom_left_mm + local_x_mm
            y_mm = self.bottom_top_edge_y_mm  # At the top edge of bottom monitor
        else:  # Top to Bottom
            x_mm = self.top_left_mm + local_x_mm
            y_mm = self.top_bottom_edge_y_mm  # At the bottom edge of top monitor
            
        self.logger.info(f"Global physical position at crossing: ({x_mm:.1f}mm, {y_mm:.1f}mm)")
        
        # Check if in direct mapping zone
        if self.has_direct_overlap and self.overlap_left_mm <= x_mm <= self.overlap_right_mm:
            self.logger.info("In direct mapping zone - using 1:1 mapping")
            
            # In direct mapping, the X coordinate stays the same (in physical space)
            # We just need to convert to local coordinates of the target monitor
            if direction == 'up':  # Bottom to Top
                # Moving to top monitor, adjust for its physical left edge
                local_target_x_mm = x_mm - self.top_left_mm
                # Target is the bottom edge of top monitor
                local_target_y_mm = self.top_monitor_height_mm
            else:  # Top to Bottom
                # Moving to bottom monitor, adjust for its physical left edge
                local_target_x_mm = x_mm - self.bottom_left_mm
                # Target is the top edge of bottom monitor
                local_target_y_mm = 0
            
            self.logger.info(f"Target local physical position: ({local_target_x_mm:.1f}mm, {local_target_y_mm:.1f}mm)")
            
            # Convert local physical position to pixel coordinates on target monitor
            new_x_px, new_y_px = target_monitor.world_to_pixels(local_target_x_mm, local_target_y_mm)
            
            # Ensure we're at the very edge of the monitor
            if direction == 'up':  # Bottom to Top
                new_y_px = target_monitor.y_offset_px + target_monitor.height_px - 1
            else:  # Top to Bottom
                new_y_px = target_monitor.y_offset_px
            
            return (new_x_px, new_y_px)
        
        # Check if we have trajectory tracking data
        elif self.in_trajectory_zone and self.trajectory_entry_point:
            self.logger.info("In trajectory zone - using vector-based mapping")
            
            # Get entry point - this is already in global physical space from tracking
            # Also includes which trajectory zone we entered from
            entry_x_px, entry_y_px, (entry_x_mm, entry_y_mm), edge_type = self.trajectory_entry_point
            
            # Calculate trajectory vector in global physical space
            dx_mm = x_mm - entry_x_mm
            dy_mm = y_mm - entry_y_mm
            
            self.logger.info(f"Entry point in global space: ({entry_x_mm:.1f}mm, {entry_y_mm:.1f}mm)")
            self.logger.info(f"Crossing point in global space: ({x_mm:.1f}mm, {y_mm:.1f}mm)")
            self.logger.info(f"Edge type: {edge_type}")
            
            # Avoid division by zero (horizontal movement)
            if abs(dy_mm) < 0.1:
                self.logger.info("Horizontal movement detected - skipping trajectory calculation")
                return None
            
            # Calculate trajectory slope
            slope = dx_mm / dy_mm
            self.logger.info(f"Trajectory vector: ({dx_mm:.1f}mm, {dy_mm:.1f}mm), slope: {slope:.2f}")
            
            # Determine target point based on the trajectory zone and direction
            # We need to map from the edge_type to the corresponding target zone
            
            if direction == 'up':  # Bottom to Top
                if edge_type == 'bottom_left':  # Left side of bottom monitor to bottom of top monitor
                    # Calculate mapping from bottom_left_trajectory source to target
                    if self.bottom_left_trajectory:
                        source = self.bottom_left_trajectory['source']
                        target = self.bottom_left_trajectory['target']
                        source_start_x, _, source_end_x, _ = source
                        target_start_x, target_y, target_end_x, _ = target
                        
                        # Calculate position within the source range (0.0 to 1.0)
                        if source_end_x > source_start_x:  # Avoid division by zero
                            position = (x_mm - source_start_x) / (source_end_x - source_start_x)
                            # Map to target range
                            target_x_mm = target_start_x + position * (target_end_x - target_start_x)
                            
                            # Convert to local coordinates of top monitor
                            local_top_x_mm = target_x_mm - self.top_left_mm
                            local_top_y_mm = self.top_monitor_height_mm  # Bottom edge
                            
                            # Convert to pixel coordinates
                            new_x_px, new_y_px = self.top_monitor.world_to_pixels(local_top_x_mm, local_top_y_mm)
                            
                            # Ensure we're at the bottom edge of top monitor
                            new_y_px = self.top_monitor.y_offset_px + self.top_monitor.height_px - 1
                            
                            self.logger.info(f"Mapped to top monitor at ({target_x_mm:.1f}mm, {target_y:.1f}mm)")
                            self.logger.info(f"Local coordinates: ({local_top_x_mm:.1f}mm, {local_top_y_mm:.1f}mm)")
                    
                    return (new_x_px, new_y_px)
                elif edge_type == 'bottom_right':  # Right side of bottom monitor
                    # Calculate mapping from bottom_right_trajectory source to target
                    if self.bottom_right_trajectory:
                        source = self.bottom_right_trajectory['source']
                        target = self.bottom_right_trajectory['target']
                        source_start_x, _, source_end_x, _ = source
                        target_start_x, target_y, target_end_x, _ = target
                        
                        # Calculate position within the source range (0.0 to 1.0)
                        if source_end_x > source_start_x:  # Avoid division by zero
                            position = (x_mm - source_start_x) / (source_end_x - source_start_x)
                            # Map to target range
                            target_x_mm = target_start_x + position * (target_end_x - target_start_x)
                            
                            # Convert to local coordinates of top monitor
                            local_top_x_mm = target_x_mm - self.top_left_mm
                            local_top_y_mm = self.top_monitor_height_mm  # Bottom edge
                            
                            # Convert to pixel coordinates
                            new_x_px, new_y_px = self.top_monitor.world_to_pixels(local_top_x_mm, local_top_y_mm)
                            
                            # Ensure we're at the bottom edge of top monitor
                            new_y_px = self.top_monitor.y_offset_px + self.top_monitor.height_px - 1
                            
                            self.logger.info(f"Mapped to top monitor at ({target_x_mm:.1f}mm, {target_y:.1f}mm)")
                            return (new_x_px, new_y_px)
                else:
                    self.logger.info(f"No valid trajectory mapping for {edge_type}")
                    return None
            
            else:  # Top to Bottom
                if edge_type == 'top_left':  # Left side of top monitor
                    # Calculate mapping from top_left_trajectory source to target
                    if self.top_left_trajectory:
                        source = self.top_left_trajectory['source']
                        target = self.top_left_trajectory['target']
                        source_start_x, _, source_end_x, _ = source
                        target_start_x, target_y, target_end_x, _ = target
                        
                        # Calculate position within the source range (0.0 to 1.0)
                        if source_end_x > source_start_x:  # Avoid division by zero
                            position = (x_mm - source_start_x) / (source_end_x - source_start_x)
                            # Map to target range
                            target_x_mm = target_start_x + position * (target_end_x - target_start_x)
                            
                            # Convert to local coordinates of bottom monitor
                            local_bottom_x_mm = target_x_mm - self.bottom_left_mm
                            local_bottom_y_mm = 0  # Top edge
                            
                            # Convert to pixel coordinates
                            new_x_px, new_y_px = self.bottom_monitor.world_to_pixels(local_bottom_x_mm, local_bottom_y_mm)
                    
                    # Set Y to top edge of bottom monitor
                    new_y_px = self.bottom_monitor.y_offset_px
                    
                elif edge_type == 'top_right':  # Right side of top monitor
                    # Calculate mapping from top_right_trajectory source to target
                    if self.top_right_trajectory:
                        source = self.top_right_trajectory['source']
                        target = self.top_right_trajectory['target']
                        source_start_x, _, source_end_x, _ = source
                        target_start_x, target_y, target_end_x, _ = target
                        
                        # Calculate position within the source range (0.0 to 1.0)
                        if source_end_x > source_start_x:  # Avoid division by zero
                            position = (x_mm - source_start_x) / (source_end_x - source_start_x)
                            # Map to target range
                            target_x_mm = target_start_x + position * (target_end_x - target_start_x)
                            
                            # Convert to local coordinates of bottom monitor
                            local_bottom_x_mm = target_x_mm - self.bottom_left_mm
                            local_bottom_y_mm = 0  # Top edge
                            
                            # Convert to pixel coordinates
                            new_x_px, new_y_px = self.bottom_monitor.world_to_pixels(local_bottom_x_mm, local_bottom_y_mm)
                            
                            # Ensure we're at the top edge of bottom monitor
                            new_y_px = self.bottom_monitor.y_offset_px
                            
                            self.logger.info(f"Mapped to bottom monitor at ({target_x_mm:.1f}mm, {target_y:.1f}mm)")
                            return (new_x_px, new_y_px)
                else:
                    self.logger.info(f"No valid trajectory mapping for {edge_type}")
                    return None
        
        else:
            self.logger.info("Not in any mapping zone or missing trajectory data - no jump")
            return None
    
    def handle_mouse_movement(self, x_px, y_px, prev_x_px, prev_y_px):
        """
        Main method to handle mouse movement and determine if a jump should occur.
        
        Args:
            x_px: Current X pixel coordinate
            y_px: Current Y pixel coordinate
            prev_x_px: Previous X pixel coordinate
            prev_y_px: Previous Y pixel coordinate
            
        Returns:
            Tuple (new_x_px, new_y_px) if jump should occur, None otherwise
        """
        # Track position for trajectory calculation
        self.track_position(x_px, y_px)
        
        # Check if we've crossed a monitor boundary
        direction = self.check_border_crossing(prev_y_px, y_px)
        
        if direction:
            # Calculate jump position
            return self.calculate_jump_position(x_px, y_px, direction)
        
        return None
