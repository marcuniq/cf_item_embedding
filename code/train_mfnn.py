import os

import pandas as pd
from gensim.models import Doc2Vec

from rec_si.recommender.mfnn import MFNNModel
from rec_si.recommender.mfnn_numpy import MFNNModelNumpy
from rec_si.recommender.user_pref_model import UserPrefModel
from rec_si.sampler.zero_sampler import ZeroSampler
from rec_si.train_eval_save import train_eval_save
from rec_si.utils import binarize_ratings, create_lookup_tables, movie_to_imdb


def train_mfnn(config):
    ratings = pd.read_csv(config['ratings_path'])

    config['nb_users'] = len(ratings['user_id'].unique())
    config['nb_movies'] = len(ratings['movie_id'].unique())

    train = pd.read_csv(config['train_path'])
    test = pd.read_csv(config['test_path'])
    val = None
    if config['val']:
        val = pd.read_csv(config['val_path'])

    zero_sampler = None
    if 'zero_sample_factor' in config:
        config['zero_samples_total'] = len(train) * config['zero_sample_factor']
        zero_sampler = ZeroSampler(ratings)

    if config['binarize']:
        train = binarize_ratings(train, pos=config['binarize_pos'], neg=config['binarize_neg'],
                                 threshold=config['binarize_threshold'])
        test = binarize_ratings(test, pos=config['binarize_pos'], neg=config['binarize_neg'],
                                threshold=config['binarize_threshold'])
        if val is not None:
            val = binarize_ratings(val, pos=config['binarize_pos'], neg=config['binarize_neg'],
                                   threshold=config['binarize_threshold'])

    d2v_model = Doc2Vec.load(config['d2v_model'])
    config['nb_d2v_features'] = int(d2v_model.docvecs['107290.txt'].shape[0])

    if config['verbose'] > 0:
        print "experiment: ", config['experiment_name']
        print config

    users, items = create_lookup_tables(ratings)
    movie_to_imdb_dict = movie_to_imdb(ratings)

    if 'theano' in config and config['theano']:
        model = MFNNModel(users, items, config, movie_to_imdb_dict)
        model.user_pref_model = UserPrefModel(config)
    else:
        model = MFNNModelNumpy(users, items, config, movie_to_imdb_dict)

    model.d2v_model = d2v_model
    loss_history = model.fit(train, val=val, test=test, zero_sampler=zero_sampler)

    return model, config, loss_history


if __name__ == "__main__":

    # make local dir the working dir, st paths are working
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)

    config = {}

    config['verbose'] = 1

    config['lr'] = 0.03
    config['lr_decay'] = 0.02
    #config['lr_power_t'] = 0.25
    config['reg_lambda'] = 0.01
    config['nb_latent_f'] = 128

    config['adagrad'] = True
    if config['adagrad']:
        config['ada_eps'] = 1e-6

    config['nb_epochs'] = 5

    config['ratings_path'] = 'data/splits/ml-100k/ratings.csv'

    config['sparse_item'] = True
    config['train_test_split'] = 0.7
    config['train_path'] = 'data/splits/ml-100k/sparse-item/0.7-train-1.csv'
    config['test_path'] = 'data/splits/ml-100k/sparse-item/0.7-test-1.csv'
    config['test'] = True

    config['val'] = False
    if config['val']:
        config['train_val_split'] = 0.8
        config['val_path'] = 'data/splits/ml-100k/sparse-item/0.7-0.8-val.csv'

    config['model_save_dir'] = 'models/mfnn'

    config['zero_sample_factor'] = 3

    config['binarize'] = True
    if config['binarize']:
        config['binarize_threshold'] = 1
        config['binarize_pos'] = 1
        config['binarize_neg'] = 0

    config['experiment_name'] = 'mfnn_ml-100k_e5_tt-0.7_nn-theano'

    config['use_avg_rating'] = False

    config['d2v_model'] = 'doc2vec-models/2016-04-14_17.36.08_20e_pv-dbow_size50_lr0.025_window8_neg5'

    config['theano'] = True
    if config['theano']:
        config['user_pref_lr'] = 0.03
        config['user_pref_lr_decay'] = 0.02
        config['user_pref_reg_lambda'] = 0.01
        config['user_pref_hidden_dim'] = [4]
        config['user_pref_input_movie_d2v'] = True

    else: # pure numpy
        config['nb_hidden_neurons'] = 4
        config['nn_reg_lambda'] = 0.01

    config['run_eval'] = True
    if config['run_eval']:
        config['precision_recall_at_n'] = 20
        config['hit_threshold'] = 4
        config['top_n_predictions'] = 100
        config['run_movie_metrics'] = True

        config['eval_in_parallel'] = True
        config['pool_size'] = 4

        config['metrics_save_dir'] = 'metrics/mfnn'

    train_eval_save(config, train_mfnn)
