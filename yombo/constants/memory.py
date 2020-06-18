MEMORY_SIZING = {
    "x_small": {  # less then 512mb
        "devices": {
            "other_device_commands": 5,
            "other_state_history": 5,
            "local_device_commands": 10,
            "local_state_history": 10,
        },
    },
    "small": {  # About 512mb
        "devices": {
            "other_device_commands": 15,
            "other_state_history": 15,
            "local_device_commands": 40,
            "local_state_history": 40,
        },
    },
    "medium": {  # About 1536mb
        "devices": {
            "other_device_commands": 40,
            "other_state_history": 40,
            "local_device_commands": 80,
            "local_state_history": 80,
        },
    },
    "large": {  # About 2048mb
        "devices": {
            "other_device_commands": 75,
            "other_state_history": 75,
            "local_device_commands": 150,
            "local_state_history": 150,
        },
    },
    "x_large": {  # About 4096mb
        "devices": {
            "other_device_commands": 150,
            "other_state_history": 150,
            "local_device_commands": 300,
            "local_state_history": 300,
        },
    },
    "xx_large": {  # About 8192mb
        "devices": {
            "other_device_commands": 300,
            "other_state_history": 300,
            "local_device_commands": 600,
            "local_state_history": 600,
        },
    },
    "xxx_large": {  # More then 2048mb
        "devices": {
            "other_device_commands": 300,
            "other_state_history": 300,
            "local_device_commands": 600,
            "local_state_history": 600,
        },
    },
}
