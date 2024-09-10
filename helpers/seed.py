import random

# Generate random seeds
def generate_random_seed():
    return random.randint(0, 2**32 - 1)
