"""Compile narrative events to deterministic OHLC animation data; Python stdlib only."""
from __future__ import annotations
import argparse
import json
import math
import random
from datetime import date
from pathlib import Path


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def compile_story(story):
    birth = date.fromisoformat(story['birth_date']) if story.get('birth_date') else None
    axis_previous = story.get('axis_start')
    if axis_previous is not None:
        axis_previous = number(axis_previous, 'axis_start')
    initial = number(story.get("initial_value"), "initial_value")
    if initial <= 0:
        raise ValueError("initial_value must be positive")
    seed = story.get("seed", 77)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    events = story.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a nonempty list")
    result = {"title": story.get("title", ""), "subject": story.get("subject", ""),
              "semantics": "fictional narrative index; not financial or historical measurements",
              "seed": seed, "initial_value": initial, "events": [], "candles": [], "markers": []}
    for key in ('axis_start', 'axis_end', 'global_view', 'overview_duration', 'music'):
        if key in story:
            result[key] = story[key]
    seen, previous_end, price, overview_started = set(), 0.0, initial, False
    for raw in events:
        if not isinstance(raw, dict):
            raise ValueError("each event must be an object")
        event_id = raw.get("id")
        if not isinstance(event_id, str) or not event_id or event_id in seen:
            raise ValueError("event ids must be nonempty unique strings")
        seen.add(event_id)
        start = number(raw.get("start"), f"{event_id}.start")
        end = number(raw.get("end"), f"{event_id}.end")
        if not math.isclose(start, previous_end, abs_tol=1e-7, rel_tol=0) or end <= start:
            raise ValueError(f"{event_id}: intervals must be contiguous, positive, and begin at zero")
        mode = raw.get("mode", "trade")
        if mode not in ("trade", "halt", "overview"):
            raise ValueError(f"{event_id}: unknown mode {mode}")
        if overview_started and mode != "overview":
            raise ValueError("overview belongs at the end; create a separate loop transition if needed")
        overview_started = overview_started or mode == "overview"
        target = number(raw.get("target", price), f"{event_id}.target")
        if target <= 0:
            raise ValueError(f"{event_id}: target must be positive")
        count = raw.get("candles", 24 if mode == "trade" else 0)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0 or count > 2000:
            raise ValueError(f"{event_id}: candles must be an integer between 0 and 2000")
        if mode == "trade" and count == 0:
            raise ValueError(f"{event_id}: trade needs at least one candle")
        if mode != "trade" and (count or not math.isclose(target, price, abs_tol=1e-7, rel_tol=0)):
            raise ValueError(f"{event_id}: halt/overview cannot trade or change price")
        volatility = number(raw.get("volatility", 0.025), f"{event_id}.volatility")
        if not 0 <= volatility <= 0.5:
            raise ValueError(f"{event_id}: volatility must be within 0..0.5")
        headline, emphasis = raw.get("headline", ""), raw.get("emphasis", [])
        if not isinstance(headline, str) or not isinstance(emphasis, list) or any(
            not isinstance(word, str) or not word or word not in headline for word in emphasis
        ):
            raise ValueError(f"{event_id}: emphasis must contain substrings of headline")
        segment = dict(raw, start=start, end=end, mode=mode, target=target,
                       candles=count, open_value=price, close_value=target)
        axis_current = raw.get('axis_year', axis_previous)
        if axis_current is not None:
            axis_current = number(axis_current, f'{event_id}.axis_year')
            if axis_previous is None or axis_current < axis_previous:
                raise ValueError(f'{event_id}: calendar axis needs a monotonic axis_start/axis_year')
            segment['axis_from'], segment['axis_to'] = axis_previous, axis_current
        if raw.get('event_date'):
            if birth is None:
                raise ValueError(f'{event_id}: event_date requires birth_date for age calculation')
            happened = date.fromisoformat(raw['event_date'])
            if happened < birth:
                raise ValueError(f'{event_id}: event occurs before birth_date')
            segment['age'] = happened.year - birth.year - ((happened.month, happened.day) < (birth.month, birth.day))
        result["events"].append(segment)
        if mode == "trade":
            rng, base = random.Random(f"{seed}:{event_id}"), price
            organic = raw.get('shape') == 'organic'
            phase = rng.uniform(0, 2 * math.pi) if organic else 0
            for index in range(count):
                p = (index + 1) / count
                progress = .65 * p + .35 * p * p * (3 - 2 * p) if organic else p
                baseline = base + (target - base) * progress
                noise = (.62 * math.sin(phase + p * math.pi * 4.6)
                         + .26 * math.sin(phase * .7 + p * math.pi * 11.4)) if organic else rng.uniform(-1, 1)
                close = target if index == count - 1 else max(
                    min(base, target) * 0.01, baseline + noise * max(base, target) * volatility * math.sin(math.pi * p)
                )
                wick = max(price, close) * volatility * 0.6
                high = max(price, close) + rng.random() * wick
                low = max(min(price, close) * 0.01, min(price, close) - rng.random() * wick)
                result["candles"].append({"event_id": event_id,
                    "t0": start + (end - start) * index / count,
                    "t1": start + (end - start) * (index + 1) / count,
                    "open": price, "high": high, "low": low, "close": close,
                    "volume": 0.2 + rng.random() * 0.6 + min(0.5, abs(close - price) / max(price, 0.01))})
                if axis_current is not None:
                    result['candles'][-1]['year0'] = axis_previous + (axis_current-axis_previous)*index/count
                    result['candles'][-1]['year1'] = axis_previous + (axis_current-axis_previous)*(index+1)/count
                price = close
        marker = raw.get("marker", "")
        if not isinstance(marker, str):
            raise ValueError(f"{event_id}: marker must be a string")
        if marker:
            result["markers"].append({"event_id": event_id, "text": marker,
                                      "time": end, "value": price, "visible_from": end})
            if axis_current is not None:
                result['markers'][-1]['year'] = axis_current
        previous_end = end
        axis_previous = axis_current
    if not result["candles"]:
        raise ValueError("story must contain at least one trade event")
    result["duration"] = previous_end
    if birth:
        result['birth_date'] = birth.isoformat()
        ages = [event['age'] for event in result['events'] if 'age' in event]
        if ages:
            result['age_range'] = [min(ages), max(ages)]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("story", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = compile_story(json.loads(args.story.read_text(encoding="utf-8-sig")))
    except (ValueError, TypeError, AttributeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"OK: {len(result['events'])} events, {len(result['candles'])} candles, {result['duration']:g}s -> {args.output}")


if __name__ == "__main__":
    main()
