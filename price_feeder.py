import concurrent.futures
import logging
import statistics
from config import *
from exchange_apis import * #TODO- remove the *, dont be lazy

logger = logging.getLogger(__name__)

def get_prices():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        res_swap = executor.submit(get_swap_price)
        res_fxs = []
        for fx_key in fx_api_option.split(","):
            if fx_key == "alphavantage":
                res_fxs.append(executor.submit(get_fx_rate))
            elif fx_key == "free_api":
                res_fxs.append(executor.submit(get_fx_rate_free))
            elif fx_key == "band":
                res_fxs.append(executor.submit(get_fx_rate_from_band))
        res_coinone = executor.submit(get_coinone_luna_price)
        res_bithumb = executor.submit(get_bithumb_luna_price)
        res_gopax = executor.submit(get_gopax_luna_price)
        res_gdac = executor.submit(get_gdac_luna_price)
        res_band = executor.submit(get_band_luna_price)
        res_binance = executor.submit(get_binance_luna_price)

    swap_price_err_flag, swap_price = res_swap.result()
    fx_err_flag, real_fx = combine_fx(res_fxs)
    coinone_err_flag, coinone_luna_price, coinone_luna_base, coinone_luna_midprice_krw = res_coinone.result()
    bithumb_err_flag, bithumb_luna_price, bithumb_luna_base, bithumb_luna_midprice_krw = res_bithumb.result()
    gopax_err_flag, gopax_luna_price, gopax_luna_base, gopax_luna_midprice_krw = res_gopax.result()
    gdac_err_flag, gdac_luna_price, gdac_luna_base, gdac_luna_midprice_krw = res_gdac.result()
    binance_err_flag, binance_luna_price = res_binance.result()
    binance_backup, coinone_backup, bithumb_backup, gdac_backup, gopax_backup = res_band.result()

    all_err_flag = fx_err_flag or coinone_err_flag or swap_price_err_flag

    if not all_err_flag:
        luna_midprice_krw = weighted_price(
            [coinone_luna_midprice_krw, bithumb_luna_midprice_krw, gopax_luna_midprice_krw, gdac_luna_midprice_krw],
            [coinone_share_default, bithumb_share_default, gopax_share_default, gdac_share_default]
        )

        prices = {}
        for denom in active_candidate:
            if denom == "ukrw":
                market_price = float(luna_midprice_krw)
            else:
                market_price = float(binance_luna_price) * real_fx[fx_map[denom]]
            prices[denom] = market_price

        if len(hardfix_active_set) == 0:
            active = [denom["denom"] for denom in swap_price["result"]]
        else:
            active = hardfix_active_set

        return prices, active
    else:
        return None, None

def combine_fx(res_fxs):
    fx_combined = {fx: [] for fx in fx_map.values()}
    all_fx_err_flag = True

    for res_fx in res_fxs:
        err_flag, fx = res_fx.result()
        all_fx_err_flag = all_fx_err_flag and err_flag
        if not err_flag:
            for key in fx_combined:
                if key in fx:
                    fx_combined[key].append(fx[key])

    for key in fx_combined:
        if fx_combined[key]:
            fx_combined[key] = statistics.median(fx_combined[key])
        else:
            fx_combined[key] = None
            all_fx_err_flag = True

    return all_fx_err_flag, fx_combined

def weighted_price(prices, weights):
    return sum(p * w for p, w in zip(prices, weights)) / sum(weights)
