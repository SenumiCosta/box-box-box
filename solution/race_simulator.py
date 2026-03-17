#!/usr/bin/env python3
"""
Box Box Box - F1 Race Simulator
Optimized syntax with preserved logic.
"""
import json
import sys
from collections import Counter

# Simulator Constants
RACE_MODELS = {
    "PACE_DELTA": {"SOFT": -1.0, "MEDIUM": 0.0, "HARD": 0.8},
    "WEAR_COEFF": {"SOFT": 0.019775, "MEDIUM": 0.010003, "HARD": 0.005055},
    "LIFE_SPAN": {"SOFT": 10, "MEDIUM": 20, "HARD": 30}
}

def run_simulation():
    # Load input from standard input
    try:
        raw_input = sys.stdin.read()
        if not raw_input:
            return
        data_packet = json.loads(raw_input)
    except json.JSONDecodeError:
        return

    event_id = data_packet['race_id']
    track_info = data_packet['race_config']
    driver_plans = data_packet['strategies']

    # Extraction of race parameters
    baseline_lap = track_info['base_lap_time']
    pit_duration = track_info['pit_lane_time']
    ambient_temp = track_info['track_temp']
    lap_limit = track_info['total_laps']

    # Environmental multiplier logic (preserved)
    if ambient_temp < 25:
        thermal_mod = 0.8
    elif ambient_temp <= 34:
        thermal_mod = 1.0
    else:
        thermal_mod = 1.3

    adjusted_wear = {comp: val * thermal_mod for comp, val in RACE_MODELS["WEAR_COEFF"].items()}
    driver_metrics = []

    # Lap-by-lap simulation loop
    for grid_tag, profile in driver_plans.items():
        pilot_id = profile['driver_id']
        pit_schedule = {ps['lap']: ps['to_tire'] for ps in profile['pit_stops']}
        
        active_compound = profile['starting_tire']
        stint_age = 1
        accumulated_time = pit_duration * len(profile['pit_stops'])
        
        for current_lap in range(1, lap_limit + 1):
            # Calculate degradation based on compound threshold
            wear_impact = max(0, stint_age - RACE_MODELS["LIFE_SPAN"][active_compound])
            lap_pace = (baseline_lap + 
                        RACE_MODELS["PACE_DELTA"][active_compound] + 
                        (wear_impact * baseline_lap * adjusted_wear[active_compound]))
            
            accumulated_time += lap_pace
            
            # Check for scheduled pit stop
            if current_lap in pit_schedule:
                active_compound = pit_schedule[current_lap]
                stint_age = 1
            else:
                stint_age += 1
        
        start_rank = int(grid_tag[3:]) # Extract number from 'posX'
        driver_metrics.append({
            "total_time": accumulated_time,
            "grid_rank": start_rank,
            "id": pilot_id,
            "initial_tire": profile['starting_tire'],
            "stops": profile['pit_stops'],
        })

    # Grouping for tie-breaker analysis
    chronometer = {}
    for entry in driver_metrics:
        chronometer.setdefault(entry["total_time"], []).append(entry)

    final_ranking = []
    for timestamp in sorted(chronometer.keys()):
        competitors = chronometer[timestamp]
        is_priority_tiebreak = False

        if len(competitors) > 1:
            start_compounds = Counter(c["initial_tire"] for c in competitors)
            
            # Specific logic for SOFT/MEDIUM mix check
            balanced_mix = (
                start_compounds.get("HARD", 0) == 0
                and start_compounds.get("SOFT", 0) == start_compounds.get("MEDIUM", 0)
                and start_compounds.get("SOFT", 0) > 0
            )
            # Check if everyone switched to HARD on a 1-stop
            standard_one_stop = all(
                len(c["stops"]) == 1 and c["stops"][0]["to_tire"] == "HARD"
                for c in competitors
            )
            is_priority_tiebreak = balanced_mix and standard_one_stop

        if is_priority_tiebreak:
            # Tire priority: SOFT > MEDIUM > HARD
            compound_priority = {"SOFT": 0, "MEDIUM": 1, "HARD": 2}
            competitors.sort(key=lambda x: (compound_priority[x["initial_tire"]], x["grid_rank"]))
        else:
            # Default to grid position
            competitors.sort(key=lambda x: x["grid_rank"])

        final_ranking.extend(competitors)

    # Final output generation
    results_output = {
        'race_id': event_id,
        'finishing_positions': [pilot["id"] for pilot in final_ranking]
    }
    sys.stdout.write(json.dumps(results_output) + '\n')

if __name__ == '__main__':
    run_simulation()