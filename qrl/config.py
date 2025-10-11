import os

# Node configuration
NODE_PORT = 9000
PEER_DISCOVERY_PORT = 9001

# Blockchain configuration
DEFAULT_DIFFICULTY = 4
INITIAL_MINING_REWARD = 100.0
MINING_REWARD = INITIAL_MINING_REWARD  # Current mining reward (will change with halvings)
TARGET_BLOCK_TIME = 60  # Target time between blocks in seconds
HALVING_INTERVAL = 210000  # Number of blocks between halvings (like Bitcoin)
HALVING_FACTOR = 0.5  # Reward is multiplied by this factor at each halving

# Difficulty adjustment configuration
DIFFICULTY_ADJUSTMENT_INTERVAL = 2016  # Blocks between difficulty adjustments (like Bitcoin)
DIFFICULTY_ADJUSTMENT_WINDOW = 2016    # Number of blocks to consider for difficulty adjustment
MIN_DIFFICULTY = 1                     # Minimum mining difficulty
MAX_DIFFICULTY = 32                    # Maximum mining difficulty

# XMSS configuration
DEFAULT_XMSS_HEIGHT = 10  # 2^10 = 1024 signatures

# Data directory
DEFAULT_DATA_DIR = os.path.expanduser("~/.qrl")

# Version
VERSION = "0.1.0"