from tqdm.auto import tqdm
from gbmi.exp_argmax_of_n.train import train_or_load_model, SEEDS, ARGMAX_OF_4_CONFIG

with tqdm(SEEDS, desc="Seed") as pbar:
    for seed in pbar:
        pbar.set_postfix({"seed": seed})
        runtime, model = train_or_load_model(
            ARGMAX_OF_4_CONFIG(seed)
        )  # , force="train"
