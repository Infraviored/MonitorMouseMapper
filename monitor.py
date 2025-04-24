#!/usr/bin/env python3

"""
Monitor Module
-------------
Handles the conversion between pixel coordinates and physical world coordinates
for individual monitors, providing a clean abstraction for monitor operations.
"""

import logging


class Monitor:
    """Represents a physical monitor with coordinate conversion methods."""
    
    def __init__(self, config_data, logger=None):
        """
        Initialize a monitor from configuration data.
        
        Args:
            config_data: Dictionary with monitor configuration (from config.json)
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.name = config_data["name"]
        
        # Physical dimensions (mm)
        self.width_mm = float(config_data["width_mm"])
        self.height_mm = float(config_data["height_mm"])
        
        # Pixel dimensions
        self.width_px = int(config_data["width"])
        self.height_px = int(config_data["height"])
        self.x_offset_px = int(config_data["x_offset"])
        self.y_offset_px = int(config_data["y_offset"])
        
        # Calculate pixels per mm (PPI factor)
        self.ppi_x = self.width_px / self.width_mm
        self.ppi_y = self.height_px / self.height_mm
        
        self.logger.info(f"Monitor {self.name}: {self.width_mm}mm × {self.height_mm}mm, "
                         f"{self.width_px}px × {self.height_px}px")
        self.logger.info(f"Monitor {self.name} PPI: {self.ppi_x:.2f}px/mm × {self.ppi_y:.2f}px/mm")
    
    def pixels_to_world(self, x_px, y_px):
        """
        Convert absolute screen pixel coordinates to physical world coordinates (mm).
        
        Args:
            x_px: Absolute X pixel coordinate
            y_px: Absolute Y pixel coordinate
            
        Returns:
            Tuple (x_mm, y_mm) with physical coordinates in mm
        """
        # Convert from absolute to monitor-relative pixel coordinates
        rel_x_px = x_px - self.x_offset_px
        rel_y_px = y_px - self.y_offset_px
        
        # Check if point is actually on this monitor
        if not (0 <= rel_x_px <= self.width_px and 0 <= rel_y_px <= self.height_px):
            self.logger.warning(f"Pixel coordinates ({x_px}, {y_px}) are outside monitor {self.name}")
        
        # Convert to physical coordinates
        x_mm = rel_x_px / self.ppi_x
        y_mm = rel_y_px / self.ppi_y
        
        return (x_mm, y_mm)
    
    def world_to_pixels(self, x_mm, y_mm):
        """
        Convert physical world coordinates (mm) to absolute screen pixel coordinates.
        
        Args:
            x_mm: X coordinate in mm (relative to monitor's left edge)
            y_mm: Y coordinate in mm (relative to monitor's top edge)
            
        Returns:
            Tuple (x_px, y_px) with absolute pixel coordinates
        """
        # Convert mm to pixels using PPI
        rel_x_px = x_mm * self.ppi_x
        rel_y_px = y_mm * self.ppi_y
        
        # Convert to absolute screen coordinates
        x_px = self.x_offset_px + rel_x_px
        y_px = self.y_offset_px + rel_y_px
        
        return (int(round(x_px)), int(round(y_px)))
    
    def is_point_on_monitor(self, x_px, y_px):
        """
        Check if an absolute pixel coordinate is on this monitor.
        
        Args:
            x_px: Absolute X pixel coordinate
            y_px: Absolute Y pixel coordinate
            
        Returns:
            True if point is within this monitor's bounds, False otherwise
        """
        rel_x_px = x_px - self.x_offset_px
        rel_y_px = y_px - self.y_offset_px
        
        return (0 <= rel_x_px <= self.width_px and 0 <= rel_y_px <= self.height_px)
    
    def get_physical_extents(self):
        """
        Get the physical extents of this monitor.
        
        Returns:
            Dictionary with width_mm, height_mm
        """
        return {
            "width_mm": self.width_mm,
            "height_mm": self.height_mm
        }
    
    def get_pixel_extents(self):
        """
        Get the pixel extents of this monitor.
        
        Returns:
            Dictionary with width_px, height_px, x_offset_px, y_offset_px
        """
        return {
            "width_px": self.width_px,
            "height_px": self.height_px,
            "x_offset_px": self.x_offset_px,
            "y_offset_px": self.y_offset_px
        }
    
    def __str__(self):
        return f"Monitor({self.name}, {self.width_mm}mm × {self.height_mm}mm, offset: ({self.x_offset_px}, {self.y_offset_px})px)"
