import pytest
import pandas as pd
import numpy as np
import statsmodels
import statsmodels.api as sm
from pandas.util.testing import (assert_series_equal,
                                 assert_numpy_array_equal)
from appelpy.utils import DummyEncoder
from appelpy.linear_model import OLS


# - MODELS -

@pytest.fixture(scope='module')
def model_mtcars_final():
    df = sm.datasets.get_rdataset('mtcars').data
    X_list = ['wt', 'qsec', 'am']
    model = OLS(df, ['mpg'], X_list)
    return model


@pytest.fixture(scope='module')
def model_cars():
    df = sm.datasets.get_rdataset('cars').data
    X_list = ['speed']
    model = OLS(df, ['dist'], X_list)
    return model


@pytest.fixture(scope='module')
def model_cars93():
    # Load data and pre-processing
    df = sm.datasets.get_rdataset('Cars93', 'MASS').data
    df.columns = (df.columns
                  .str.replace(r"[ ,.,-]", '_')
                  .str.lower())
    # Dummy columns
    dummy_encoder = DummyEncoder(df, separator='_')
    df = dummy_encoder.encode({'type': 'Compact',
                               'airbags': 'None',
                               'origin': 'USA'})
    df.columns = (df.columns
                  .str.replace(r"[ ,.,-]", '_')
                  .str.lower())
    # Model
    X_list = ['type_large', 'type_midsize', 'type_small',
              'type_sporty', 'type_van',
              'mpg_city',
              'airbags_driver_&_passenger', 'airbags_driver_only',
              'origin_non_usa']
    model = OLS(df, ['price'], X_list)
    return model


@pytest.fixture(scope='module')
def model_caschools():
    df = sm.datasets.get_rdataset('Caschool', 'Ecdat').data

    # Square income
    df['avginc_sq'] = df['avginc'] ** 2

    # Model
    X_list = ['avginc', 'avginc_sq']
    model = OLS(df, ['testscr'], X_list)
    return model


# - TESTS -


def test_coefficients(model_mtcars_final):
    expected_coef = pd.Series({'const': 9.6178,
                               'wt': -3.9165,
                               'qsec': 1.2259,
                               'am': 2.9358})
    assert_series_equal(model_mtcars_final.results.params.round(4),
                        expected_coef)

    assert isinstance(model_mtcars_final.results_output,
                      statsmodels.iolib.summary.Summary)
    assert isinstance(model_mtcars_final.results_output_standardized,
                      pd.io.formats.style.Styler)


def test_coefficients_beta(model_cars93):
    expected_coefs = pd.Series({'type_large': 0.10338,
                                'type_midsize': 0.22813,
                                'type_small': -0.01227,
                                'type_sporty': 0.01173,
                                'type_van': -0.02683,
                                'mpg_city': -0.46296,
                                'airbags_driver_&_passenger': 0.34998,
                                'airbags_driver_only': 0.23687,
                                'origin_non_usa': 0.26742},
                               name='coef_stdXy')
    expected_coefs.index.name = 'price'
    assert_series_equal((model_cars93
                         .results_output_standardized
                         .data['coef_stdXy']
                         .round(5)),
                        expected_coefs)


def test_standard_errors(model_mtcars_final):
    expected_se = pd.Series({'const': 6.9596,
                             'wt': 0.7112,
                             'qsec': 0.2887,
                             'am': 1.4109})
    assert_series_equal(model_mtcars_final.results.bse.round(4),
                        expected_se)

    assert(model_mtcars_final.cov_type == 'nonrobust')


def test_t_scores(model_mtcars_final):
    expected_t_score = pd.Series({'const': 1.382,
                                  'wt': -5.507,
                                  'qsec': 4.247,
                                  'am': 2.081})
    assert_series_equal(model_mtcars_final.results.tvalues.round(3),
                        expected_t_score)
    assert model_mtcars_final.results.use_t


def test_model_selection_stats(model_mtcars_final):
    expected_root_mse = 2.459
    expected_r_squared = 0.8497
    expected_r_squared_adj = 0.8336

    assert(np.round((model_mtcars_final
                     .model_selection_stats['Root MSE']), 3)
           == expected_root_mse)
    assert(np.round((model_mtcars_final
                     .model_selection_stats['R-squared']), 4)
           == expected_r_squared)
    assert(np.round((model_mtcars_final
                     .model_selection_stats['R-squared (adj)']), 4)
           == expected_r_squared_adj)


def test_significant_regressors(model_mtcars_final):
    expected_regressors_000001 = []
    expected_regressors_001 = ['wt', 'qsec']  # 0.1% sig
    expected_regressors_01 = ['wt', 'qsec']  # 1% sig
    expected_regressors_05 = ['wt', 'qsec', 'am']  # 5% sig

    assert (model_mtcars_final.significant_regressors(0.000001)
            == expected_regressors_000001)
    assert (model_mtcars_final.significant_regressors(0.001)
            == expected_regressors_001)
    assert (model_mtcars_final.significant_regressors(0.01)
            == expected_regressors_01)
    assert (model_mtcars_final.significant_regressors(0.05)
            == expected_regressors_05)

    with pytest.raises(TypeError):
        model_mtcars_final.significant_regressors('str')

    with pytest.raises(ValueError):
        model_mtcars_final.significant_regressors(np.inf)
    with pytest.raises(TypeError):
        model_mtcars_final.significant_regressors(0)
    with pytest.raises(TypeError):
        model_mtcars_final.significant_regressors(-1)
    with pytest.raises(ValueError):
        model_mtcars_final.significant_regressors(0.11)


def test_other_attributes(model_mtcars_final):
    # Weights
    expected_w = np.ones(32)
    assert_numpy_array_equal(model_mtcars_final.w.to_numpy(), expected_w)
    assert isinstance(model_mtcars_final.w, pd.Series)

    # X and y
    assert isinstance(model_mtcars_final.X, pd.DataFrame)
    assert isinstance(model_mtcars_final.y, pd.Series)

    # Residuals
    expected_resid_standardized = (
        np.array([-0.62542, -0.49419, -1.48858,  0.22975,  0.72174, -1.17901,
                  -0.33191,  1.17731, -1.23866,  0.2607, -0.63558,  0.58422,
                  0.29971, -0.70185, -0.32268,  0.08537,  2.15973,  2.00067,
                  0.636,  1.82147, -1.33149, -0.43212, -0.92224, -0.0748,
                  1.5755, -0.36299,  0.5794,  1.35596, -0.94227, -0.43467,
                  -0.66451, -1.333])
    )
    assert_numpy_array_equal(np.round(model_mtcars_final
                                      .resid_standardized.to_numpy(), 5),
                             expected_resid_standardized)

    # y_standardized
    expected_y_standardized = (
        np.array([0.15088,  0.15088,  0.44954,  0.21725, -0.23073, -0.33029,
                  -0.96079,  0.71502,  0.44954, -0.14777, -0.38006, -0.61235,
                  -0.46302, -0.81146, -1.60788, -1.60788, -0.89442,  2.04239,
                  1.71055,  2.29127,  0.23385, -0.76168, -0.81146, -1.12671,
                  -0.14777,  1.19619,  0.98049,  1.71055, -0.71191, -0.06481,
                  -0.84464,  0.21725])
    )
    assert_numpy_array_equal(np.round(model_mtcars_final.y_standardized
                                      .to_numpy(), 5),
                             expected_y_standardized)

    # X_standardized col
    expected_qsec_standardized = (
        np.array([-0.77717, -0.46378,  0.42601,  0.89049, -0.46378,  1.32699,
                  -1.12413,  1.20387,  2.82675,  0.25253,  0.5883, -0.25113,
                  -0.1392,  0.08464,  0.07345, -0.01609, -0.23993,  0.90728,
                  0.37564,  1.14791,  1.20947, -0.54772, -0.30709, -1.36476,
                  -0.44699,  0.5883, -0.64286, -0.53093, -1.87401, -1.3144,
                  -1.81805,  0.42041])
    )
    assert_numpy_array_equal(np.round(model_mtcars_final.X_standardized['qsec']
                                      .to_numpy(), 5),
                             expected_qsec_standardized)


def test_predictions(model_caschools):
    # Est effect of avg 10 -> 11:
    expected_y_hat_diff = 2.9625
    actual_y_hat_diff = (model_caschools.predict(pd.Series([11, 11 ** 2])) -
                         model_caschools.predict(pd.Series([10, 10 ** 2])))[0]
    assert np.round(actual_y_hat_diff, 4) == expected_y_hat_diff

    # Est effect of avg 40 -> 41:
    expected_y_hat_diff = 0.4240
    actual_y_hat_diff = (model_caschools.predict(pd.Series([41, 41 ** 2])) -
                         model_caschools.predict(pd.Series([40, 40 ** 2])))[0]
    assert np.round(actual_y_hat_diff, 4) == expected_y_hat_diff

    with pytest.raises(ValueError):
        model_caschools.predict(pd.Series([41]))
