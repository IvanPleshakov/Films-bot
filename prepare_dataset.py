import pandas as pd
import numpy as np
import os
import random
import datetime
import string

FILMS_PATH = 'https://drive.google.com/file/d/1ChC0NpO0eCn7spVA1ezBVBlVQQD9xAae/view?usp=sharing'

file_id = FILMS_PATH.split('/')[-2]
dwn_url = 'https://drive.google.com/uc?id=' + file_id
dataset = pd.read_csv(dwn_url)

def set_seed(seed):
    np.random.seed(seed)
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)

set_seed(0)
dataset = dataset.sample(frac=1)
dataset['Жанр_массив'] = dataset['Жанр'].apply(lambda x: x.translate(str.maketrans('', '', string.punctuation))).str.split(' ')

# ----------------------------------------------------------------------------------------------------------------

set_seed(0)
days = np.random.choice(np.arange(len(dataset)), 366)
day_film = days[datetime.datetime.now().timetuple().tm_yday]