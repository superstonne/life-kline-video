"""Behavioral verification for the installed narrative OHLC compiler."""
import copy
import importlib.util
import json
from pathlib import Path

skill = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_chart", skill / "scripts/build_chart.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
story = json.loads((skill / "assets/example-story.json").read_text(encoding="utf-8"))
chart = module.compile_story(story)
assert chart == module.compile_story(story), "nondeterministic output"
previous = story["initial_value"]
for candle in chart["candles"]:
    assert candle["open"] == previous, "broken price continuity"
    assert 0 < candle["low"] <= min(candle["open"], candle["close"])
    assert candle["high"] >= max(candle["open"], candle["close"])
    assert candle["t0"] < candle["t1"]
    previous = candle["close"]
for event in chart["events"]:
    candles = [c for c in chart["candles"] if c["event_id"] == event["id"]]
    if event["mode"] == "trade":
        assert len(candles) == event["candles"]
        assert candles[-1]["close"] == event["target"]
        assert candles[0]["t0"] == event["start"]
        assert candles[-1]["t1"] == event["end"]
    else:
        assert not candles, "halt/overview emitted candles"
for marker in chart["markers"]:
    event = next(e for e in chart["events"] if e["id"] == marker["event_id"])
    assert marker["visible_from"] == event["end"]
    assert marker["value"] == event["close_value"]

invalid = []
bad = copy.deepcopy(story); bad["events"][1]["target"] += 1; invalid.append(bad)
bad = copy.deepcopy(story); bad["events"][1]["start"] += 1; invalid.append(bad)
bad = copy.deepcopy(story); bad["events"][0]["target"] = float("nan"); invalid.append(bad)
bad = copy.deepcopy(story); bad["events"][1]["id"] = "learn"; invalid.append(bad)
bad = copy.deepcopy(story); bad["events"][0]["candles"] = 0; invalid.append(bad)
bad = copy.deepcopy(story); bad["events"][1]["axis_year"] = 2000; invalid.append(bad)
bad = copy.deepcopy(story); bad["birth_date"] = '2030-01-01'; invalid.append(bad)
for bad in invalid:
    try:
        module.compile_story(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid story accepted")
tiny = {"initial_value":1e-6, "events":[{"id":"tiny","start":0,"end":1,"target":2e-6}]}
for c in module.compile_story(tiny)["candles"]:
    assert 0 < c["low"] <= min(c["open"], c["close"])
assert all(c['year0'] <= c['year1'] for c in chart['candles'])
for a,b in zip(chart['candles'],chart['candles'][1:]):
    assert a['year1']<=b['year0']+1e-9
for when,expected in [('2018-03-14',21),('2018-03-15',22)]:
    dated=copy.deepcopy(story);dated['events'][0]['event_date']=when
    assert module.compile_story(dated)['events'][0]['age']==expected
print("PASS: determinism, continuity, OHLC, endpoints, halt/overview, markers, calendar order, birthday ages, seven invalid inputs, tiny positive prices")
