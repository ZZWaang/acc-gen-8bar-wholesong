import pretty_midi as pm
import json
import sys
import re
import os
import mir_eval
import numpy as np


DEFAULT_V_MEL = 70
DEFAULT_V_ACC = 50
DEFAULT_V_CHD = 50


def load_json(json_fn):

    with open(json_fn, 'r') as json_file:
        data_dict = json.load(json_file)
    return data_dict


def note_list_to_notes(note_list, default_v, bpm):
    notes = []
    for note in note_list:
        start = note['start'] * 0.25 * 60 / bpm
        end = start + note['duration'] * 0.25 * 60 / bpm
        notes.append(pm.Note(velocity=default_v, pitch=note['pitch'], start=start, end=end))
    return notes


def chord_list_to_notes(chord_list, default_v, bpm):
    notes = []
    for chord in chord_list:
        start = chord['start'] * 0.25 * 60 / bpm
        end = start + chord['duration'] * 0.25 * 60 / bpm
        
        chord_repr = mir_eval.chord.encode(chord['symbol'])
        if (chord_repr[1] == 0).all():
            continue
        bass = (chord_repr[0] + chord_repr[2]) % 12
        notes.append(pm.Note(velocity=default_v, pitch=bass + 36, start=start, end=end))
        chroma = np.roll(chord_repr[1], shift=chord_repr[0])
        chroma_p = np.where(chroma)[0]
        for p in chroma_p:
            notes.append(pm.Note(velocity=default_v, pitch=p + 48, start=start, end=end))
    return notes


def find_generation_file_paths(generation_path):
    pattern = re.compile(r'generation_(\d+)\.json')
    files = [os.path.join(generation_path, fn) for fn in os.listdir(generation_path) if pattern.match(fn)]
    file_ids = [re.search(pattern, fn).group(1) for fn in os.listdir(generation_path) if pattern.match(fn)]
    return files, file_ids


def main(lead_sheet_fn, acc_folder_path, output_folder_path, bpm):
    """Create midi of the input lead sheet and generated accompaniments"""
    os.makedirs(output_folder_path, exist_ok=True)

    # load lead sheet json data
    lead_sheet_dict = load_json(lead_sheet_fn)
    melody_notes = note_list_to_notes(lead_sheet_dict['melody'], default_v=DEFAULT_V_MEL, bpm=bpm)
    chord_notes = chord_list_to_notes(lead_sheet_dict['chords'], default_v=DEFAULT_V_CHD, bpm=bpm)

    # create midi demo of lead sheet (melody + chord)
    midi = pm.PrettyMIDI(initial_tempo=bpm)
    midi.instruments = [pm.Instrument(65, is_drum=False, name='melody'), 
                        pm.Instrument(0, is_drum=False, name='chords')
                        ]
    midi.instruments[0].notes = melody_notes
    midi.instruments[1].notes = chord_notes
    midi.write(os.path.join(output_folder_path, f'demo_lead_sheet.mid'))

    # find all generated samples
    acc_jsons, acc_ids = find_generation_file_paths(acc_folder_path)


    for acc_json, acc_id in zip(acc_jsons, acc_ids):
        # load acc json data
        acc_dict = load_json(acc_json)
        acc_notes = note_list_to_notes(acc_dict['acc'], default_v=DEFAULT_V_ACC, bpm=bpm)
        
        # create midi demo of each generation (melody + acc)
        midi = pm.PrettyMIDI(initial_tempo=bpm)
        midi.instruments = [pm.Instrument(65, is_drum=False, name='melody'), 
                            pm.Instrument(0, is_drum=False, name='accompaniment')
                            ]
        midi.instruments[0].notes = melody_notes
        midi.instruments[1].notes = acc_notes
        midi.write(os.path.join(output_folder_path, f'demo_generation_{acc_id}.mid'))
    


if __name__ == '__main__':

    lead_sheet_json_fn = sys.argv[1]
    acc_folder_path = sys.argv[2]
    output_folder_path = sys.argv[3]
    bpm = int(sys.argv[4])

    main(lead_sheet_json_fn, acc_folder_path, output_folder_path, bpm)
