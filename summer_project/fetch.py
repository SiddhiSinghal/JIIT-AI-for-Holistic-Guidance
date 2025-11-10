from datasets import load_dataset

# Load the dataset
ds = load_dataset("thu-coai/augesc")

# Choose a split (e.g., "train")
split = ds["train"]

# Save to JSON only
split.to_json("augesc_train.json")
