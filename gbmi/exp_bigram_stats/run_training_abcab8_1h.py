# %%
from gbmi.exp_bigram_stats.train import ABCAB8_BIGRAM1H, BigramTrainingWrapper
from gbmi.model import train_or_load_model

# %%
print(ABCAB8_BIGRAM1H)
print(BigramTrainingWrapper.build_model(ABCAB8_BIGRAM1H).cfg)
_, model = train_or_load_model(ABCAB8_BIGRAM1H, force="train")
