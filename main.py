"""Crypto trend bot.

  python main.py backtest                 # download history and backtest
  python main.py backtest --demo          # offline test on synthetic data
  python main.py optimize                 # grid-search EMA lengths on history
  python main.py paper                    # live data, simulated money
  python main.py paper --reset            # wipe paper account and start fresh
  python main.py dashboard                # open the dashboard at http://localhost:8765
  python main.py paper --dashboard        # paper bot + dashboard together
"""
import argparse
import itertools
import copy
from pathlib import Path

from bot.backtest import run_backtest, save_report
from bot.data import load_history, synthetic
from bot.util import load_config, setup_logging


def print_stats(stats):
    print("\n" + "=" * 46)
    for k, v in stats.items():
        print(f"  {k:<20} {v}")
    print("=" * 46)


def cmd_backtest(cfg, args):
    log = setup_logging(cfg, "backtest")
    df = synthetic() if args.demo else load_history(cfg)
    log.info(f"Loaded {len(df)} candles ({df.index[0]} -> {df.index[-1]})")
    stats, trades, eq, full = run_backtest(df, cfg)
    print_stats(stats)
    out = save_report(stats, trades, eq, full, cfg)
    log.info(f"Saved trades, equity curve and chart to {out}/")


def cmd_optimize(cfg, args):
    log = setup_logging(cfg, "optimize")
    df = synthetic() if args.demo else load_history(cfg)
    split = int(len(df) * 0.7)
    train, test = df.iloc[:split], df.iloc[split:]
    results = []
    for fast, slow in itertools.product([9, 12, 20, 30], [26, 50, 100]):
        if fast >= slow:
            continue
        c = copy.deepcopy(cfg)
        c["strategy"].update(ema_fast=fast, ema_slow=slow)
        s, *_ = run_backtest(train, c)
        results.append((s["sharpe"], fast, slow, s))
    results.sort(reverse=True, key=lambda r: r[0])
    print("\nTop settings on first 70% of data (in-sample):")
    for sh, f, sl, s in results[:5]:
        print(f"  EMA {f:>3}/{sl:<3}  sharpe {sh:>5}  return {s['total_return_pct']:>7}%  maxDD {s['max_drawdown_pct']}%  trades {s['trades']}")
    _, f, sl, _ = results[0]
    c = copy.deepcopy(cfg)
    c["strategy"].update(ema_fast=f, ema_slow=sl)
    s, *_ = run_backtest(test, c)
    print(f"\nBest ({f}/{sl}) on the unseen last 30% (out-of-sample):")
    print_stats(s)
    print("If out-of-sample is much worse than in-sample, the settings are overfit. Don't trust them.")
    log.info("Optimization done")


def cmd_paper(cfg, args):
    from bot.paper import PaperTrader

    if args.reset:
        Path(cfg["paper"]["state_file"]).unlink(missing_ok=True)
    log = setup_logging(cfg, "paper")
    if args.dashboard:
        from bot.server import serve
        serve(cfg, log, background=True)
    PaperTrader(cfg, log).run(once=args.once)


def cmd_dashboard(cfg, args):
    from bot.server import serve
    serve(cfg, setup_logging(cfg, "dashboard"))


def main():
    ap = argparse.ArgumentParser(description="Crypto EMA/RSI trend bot")
    ap.add_argument("mode", choices=["backtest", "optimize", "paper", "dashboard"])
    ap.add_argument("-c", "--config", default="config.yaml")
    ap.add_argument("--demo", action="store_true", help="use synthetic data (no internet needed)")
    ap.add_argument("--reset", action="store_true", help="paper: start a fresh account")
    ap.add_argument("--dashboard", action="store_true", help="paper: also serve the dashboard")
    ap.add_argument("--once", action="store_true", help="paper: run a single check and exit")
    args = ap.parse_args()
    cfg = load_config(args.config)
    {"backtest": cmd_backtest, "optimize": cmd_optimize, "paper": cmd_paper, "dashboard": cmd_dashboard}[args.mode](cfg, args)


if __name__ == "__main__":
    main()
