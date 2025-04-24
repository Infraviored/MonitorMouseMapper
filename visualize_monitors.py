#!/usr/bin/env python3

import json
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def load_config(config_path):
    """Load monitor configuration from json file."""
    with open(config_path, 'r') as f:
        return json.load(f)

def visualize_monitor_mapping(config):
    """Create a visualization of monitor physical mappings and jump zones."""
    # Extract monitor information
    monitors = config['monitors']
    top_monitor_name = config['top_monitor']
    bottom_monitor_name = config['bottom_monitor']
    
    # Find our monitors in the config
    top_monitor = next(m for m in monitors if m['name'] == top_monitor_name)
    bottom_monitor = next(m for m in monitors if m['name'] == bottom_monitor_name)
    
    # Get physical and pixel dimensions
    top_width_mm = float(top_monitor['width_mm'])
    top_height_mm = float(top_monitor['height_mm'])
    top_width_px = int(top_monitor['width'])
    top_height_px = int(top_monitor['height'])
    top_x_offset_px = int(top_monitor['x_offset'])
    top_y_offset_px = int(top_monitor['y_offset'])
    
    bottom_width_mm = float(bottom_monitor['width_mm'])
    bottom_height_mm = float(bottom_monitor['height_mm'])
    bottom_width_px = int(bottom_monitor['width'])
    bottom_height_px = int(bottom_monitor['height'])
    bottom_x_offset_px = int(bottom_monitor['x_offset'])
    bottom_y_offset_px = int(bottom_monitor['y_offset'])
    
    # Calculate pixels per mm (PPI) for each monitor
    top_ppi = top_width_px / top_width_mm
    bottom_ppi = bottom_width_px / bottom_width_mm
    
    print(f"Monitor PPI (pixels per mm):")
    print(f"  Top ({top_monitor_name}): {top_ppi:.2f}")
    print(f"  Bottom ({bottom_monitor_name}): {bottom_ppi:.2f}")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(15, 10))
    
    # Draw monitors based on their physical dimensions
    # Use pixel offsets to calculate where the monitors are physically
    
    # Since we're visualizing in physical space, we need to convert pixel offsets to mm
    # For simplicity, we'll place the monitors adjacent vertically
    # with their horizontal positions determined by their X offsets
    
    # Bottom monitor is drawn at (0,0) as reference
    bottom_x_mm = 0
    bottom_y_mm = 0
    
    # Top monitor is placed directly above bottom monitor
    # We calculate its horizontal offset relative to bottom monitor
    rel_x_offset_px = top_x_offset_px - bottom_x_offset_px
    rel_x_offset_mm = rel_x_offset_px / top_ppi  # Convert to mm using top monitor's PPI
    
    top_x_mm = bottom_x_mm + rel_x_offset_mm
    top_y_mm = bottom_y_mm + bottom_height_mm  # Directly on top of bottom monitor
    
    # Draw the monitors with their physical dimensions
    bottom_rect = patches.Rectangle(
        (bottom_x_mm, bottom_y_mm), 
        bottom_width_mm, bottom_height_mm,
        linewidth=2, edgecolor='blue', facecolor='lightyellow', alpha=0.5
    )
    ax.add_patch(bottom_rect)
    
    top_rect = patches.Rectangle(
        (top_x_mm, top_y_mm), 
        top_width_mm, top_height_mm,
        linewidth=2, edgecolor='blue', facecolor='lightblue', alpha=0.5
    )
    ax.add_patch(top_rect)
    
    # Calculate direct correspondence zones where monitors physically overlap
    # Physical overlap is determined by comparing horizontal extents
    
    # Calculate left and right edges of each monitor in mm
    top_left_mm = top_x_mm
    top_right_mm = top_x_mm + top_width_mm
    bottom_left_mm = bottom_x_mm
    bottom_right_mm = bottom_x_mm + bottom_width_mm
    
    # Calculate overlap range
    overlap_left_mm = max(top_left_mm, bottom_left_mm)
    overlap_right_mm = min(top_right_mm, bottom_right_mm)
    
    # Check if there is actual overlap
    has_overlap = overlap_right_mm > overlap_left_mm
    
    # Draw direct correspondence zones (red lines) for areas with 1:1 mapping
    if has_overlap:
        # Direct mapping zone on top monitor
        direct_top_line = plt.Line2D(
            [overlap_left_mm, overlap_right_mm], 
            [top_y_mm, top_y_mm],
            lw=3, color='red', alpha=0.8
        )
        ax.add_line(direct_top_line)
        
        # Direct mapping zone on bottom monitor
        direct_bottom_line = plt.Line2D(
            [overlap_left_mm, overlap_right_mm], 
            [bottom_y_mm + bottom_height_mm, bottom_y_mm + bottom_height_mm],
            lw=3, color='red', alpha=0.8
        )
        ax.add_line(direct_bottom_line)
        
        print(f"Direct mapping zone (mm): {overlap_left_mm:.1f} - {overlap_right_mm:.1f}")
    else:
        print("No direct overlap between monitors")
    
    # Draw trajectory zones (green lines) for areas without direct mapping
    # Top monitor trajectory zones (if any)
    if top_left_mm < overlap_left_mm:
        # Left trajectory zone on top monitor
        top_left_traj = plt.Line2D(
            [top_left_mm, overlap_left_mm], 
            [top_y_mm, top_y_mm],
            lw=3, color='green', alpha=0.8
        )
        ax.add_line(top_left_traj)
        print(f"Top left trajectory zone (mm): {top_left_mm:.1f} - {overlap_left_mm:.1f}")
    
    if top_right_mm > overlap_right_mm:
        # Right trajectory zone on top monitor
        top_right_traj = plt.Line2D(
            [overlap_right_mm, top_right_mm], 
            [top_y_mm, top_y_mm],
            lw=3, color='green', alpha=0.8
        )
        ax.add_line(top_right_traj)
        print(f"Top right trajectory zone (mm): {overlap_right_mm:.1f} - {top_right_mm:.1f}")
    
    # Bottom monitor trajectory zones (if any)
    if bottom_left_mm < overlap_left_mm:
        # Left trajectory zone on bottom monitor
        bottom_left_traj = plt.Line2D(
            [bottom_left_mm, overlap_left_mm], 
            [bottom_y_mm + bottom_height_mm, bottom_y_mm + bottom_height_mm],
            lw=3, color='green', alpha=0.8
        )
        ax.add_line(bottom_left_traj)
        print(f"Bottom left trajectory zone (mm): {bottom_left_mm:.1f} - {overlap_left_mm:.1f}")
    
    if bottom_right_mm > overlap_right_mm:
        # Right trajectory zone on bottom monitor
        bottom_right_traj = plt.Line2D(
            [overlap_right_mm, bottom_right_mm], 
            [bottom_y_mm + bottom_height_mm, bottom_y_mm + bottom_height_mm],
            lw=3, color='green', alpha=0.8
        )
        ax.add_line(bottom_right_traj)
        print(f"Bottom right trajectory zone (mm): {overlap_right_mm:.1f} - {bottom_right_mm:.1f}")
    
    # Draw example trajectory vectors from bottom to top
    # Choose a point in a trajectory zone if there is one, otherwise no arrows
    
    if has_overlap and (bottom_left_mm < overlap_left_mm or bottom_right_mm > overlap_right_mm):
        # Draw a trajectory that successfully hits the top monitor
        if bottom_left_mm < overlap_left_mm:
            # Start in left trajectory zone
            start_x = bottom_left_mm + (overlap_left_mm - bottom_left_mm) / 2
            start_y = bottom_y_mm + bottom_height_mm
            
            # End on the top monitor
            end_x = overlap_left_mm + min(100, (overlap_right_mm - overlap_left_mm) / 2)
            end_y = top_y_mm
            
            success_arrow = patches.FancyArrowPatch(
                (start_x, start_y), (end_x, end_y),
                connectionstyle="arc3,rad=.2", 
                arrowstyle="Simple,head_width=10,head_length=10", 
                color="darkgreen", lw=2
            )
            ax.add_patch(success_arrow)
            ax.text(start_x - 30, (start_y + end_y) / 2, "Hit\nTarget", 
                    color="darkgreen", fontsize=10, ha="right")
        
        # Draw a trajectory that misses the top monitor
        if bottom_right_mm > overlap_right_mm:
            # Start in right trajectory zone
            start_x = overlap_right_mm + (bottom_right_mm - overlap_right_mm) / 2
            start_y = bottom_y_mm + bottom_height_mm
            
            # End beyond the top monitor's edge
            end_x = start_x + 50  # Miss to the right
            end_y = top_y_mm + top_height_mm / 2
            
            fail_arrow = patches.FancyArrowPatch(
                (start_x, start_y), (end_x, end_y),
                connectionstyle="arc3,rad=-.2", 
                arrowstyle="Simple,head_width=10,head_length=10", 
                color="darkred", lw=2, linestyle="--"
            )
            ax.add_patch(fail_arrow)
            ax.text(end_x + 10, end_y, "Miss\nTarget", 
                    color="darkred", fontsize=10)
    
    # Add monitor labels with both mm and px dimensions
    ax.text(top_x_mm + top_width_mm/2, top_y_mm + top_height_mm/2, 
            f"Top Monitor ({top_monitor_name})\n{top_width_mm:.1f}mm × {top_height_mm:.1f}mm\n{top_width_px}px × {top_height_px}px",
            ha='center', va='center', fontsize=12)
    
    ax.text(bottom_x_mm + bottom_width_mm/2, bottom_y_mm + bottom_height_mm/2, 
            f"Bottom Monitor ({bottom_monitor_name})\n{bottom_width_mm:.1f}mm × {bottom_height_mm:.1f}mm\n{bottom_width_px}px × {bottom_height_px}px",
            ha='center', va='center', fontsize=12)
    
    # Add legend
    red_patch = patches.Patch(color='red', label='Direct Correspondence Zone (1:1 Mapping)')
    green_patch = patches.Patch(color='green', label='Trajectory Zone (Vector-Based Mapping)')
    darkgreen_arrow = patches.Patch(color='darkgreen', label='Successful Trajectory (Hits Monitor)')
    darkred_arrow = patches.Patch(color='darkred', label='Failed Trajectory (No Target)')
    ax.legend(handles=[red_patch, green_patch, darkgreen_arrow, darkred_arrow], 
              loc='upper right', fontsize=9)
    
    # Set axis limits with padding
    all_x = [top_x_mm, bottom_x_mm, top_x_mm + top_width_mm, bottom_x_mm + bottom_width_mm]
    all_y = [top_y_mm, bottom_y_mm, top_y_mm + top_height_mm, bottom_y_mm + bottom_height_mm]
    
    padding = 50  # mm
    ax.set_xlim(min(all_x) - padding, max(all_x) + padding)
    ax.set_ylim(min(all_y) - padding, max(all_y) + padding)
    
    # Set labels and title
    ax.set_xlabel('Physical Width (mm)')
    ax.set_ylabel('Physical Height (mm)')
    ax.set_title('Monitor Physical Mapping Visualization\nShowing Direct Correspondence and Trajectory Zones')
    
    # Add a grid for better readability
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Save the visualization
    plt.tight_layout()
    plt.savefig('monitor_mapping_visualization.png', dpi=150)
    print(f"Visualization saved as 'monitor_mapping_visualization.png'")
    
    # Show the plot
    plt.show()


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        exit(1)
    
    config = load_config(config_path)
    visualize_monitor_mapping(config)