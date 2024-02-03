from gbmi.exp_f_g.train import f_g_TrainingWrapper
from gbmi.exp_f_g.functions import add_sub, max_min

from gbmi.exp_f_g.train import f_g_config

from gbmi.model import train_or_load_model

import torch
import einops
from torch import tensor
from math import *
import tqdm

device = "cuda"

# functions=[("max","min"),("is_sorted","exactly_2_of_3_even"),("add","minus")]

# add_sub_1_head_CONFIG = f_g_config(fun=add_sub(53, 2), n_head=1, elements=2)
# add_sub_2_head_CONFIG = f_g_config(fun=add_sub(53, 2), n_head=2, elements=2)
add_sub_4_head_CONFIG = f_g_config(fun=add_sub(53, 2), n_head=4, elements=2)
# max_min_1_head_CONFIG = f_g_config(fun=max_min(53, 2), n_head=1, elements=2)
# max_min_2_head_CONFIG = f_g_config(fun=max_min(53, 2), n_head=2, elements=2)

# runtime_add_sub_1, model_add_sub_1 = train_or_load_model(add_sub_1_head_CONFIG)
# runtime_add_sub_2, model_add_sub_2 = train_or_load_model(add_sub_2_head_CONFIG)
runtime_add_sub_4, model_add_sub_4 = train_or_load_model(add_sub_4_head_CONFIG)
# runtime_max_min_1, model_max_min_1 = train_or_load_model(max_min_1_head_CONFIG)
# runtime_max_min_2, model_max_min_2 = train_or_load_model(max_min_2_head_CONFIG)

# model_add_sub_1.to(device)
# model_add_sub_2.to(device)
# model_max_min_1.to(device)
# model_max_min_2.to(device)
