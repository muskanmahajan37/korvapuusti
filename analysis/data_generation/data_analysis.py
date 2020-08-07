# Lint as: python3
"""Functionality to plot and save the data generated by data_generation.py.

Copyright 2020 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""
import collections
import csv
import itertools
import json
import os
import random
from typing import List, Any, Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

import loudness
import data_generation


def find_stft_bin(frequency: float, window_size=2048, sample_rate=44100) -> int:
  """Finds the correct bin for a frequency in a signal processed by a STFT.

  Bins in a STFT go from 0 to sample_rate. The window_size must be a power of 2
  for FFT.

  Args:
    frequency: frequency to look for
    window_size: window size used in STFT
    sample_rate: sample rate of signal processed by STFT

  Returns:
    Index of the bin containing the frequency.
  """
  step_size = sample_rate / window_size
  return int(frequency / step_size)


def plot_histogram(values: List[Any], path: str, bins=None, logscale=False,
                   x_label="", title=""):
  """Plots and saves a histogram."""
  _, ax = plt.subplots(1, 1)
  if not bins:
    ax.hist(values, histtype="stepfilled", alpha=0.2)
  else:
    ax.hist(values, bins=bins, histtype="stepfilled", alpha=0.2)
  if logscale:
    plt.xscale("log")
  ax.set_ylabel("Occurrence Count")
  ax.set_xlabel(x_label)
  ax.set_title(title)
  plt.savefig(path)


def plot_histograms(plot_directory: str,
                    covered_frequencies: List[float], covered_phons: List[int],
                    covered_num_tones: List[int],
                    covered_levels: List[int]):
  """Plots and saves multiple histograms."""
  plot_histogram(covered_phons, os.path.join(plot_directory, "phons_hist.png"),
                 x_label="Loudness (phons)",
                 title="Distribution of Phons Levels in Data")
  plot_histogram(covered_levels, os.path.join(plot_directory,
                                              "levels_hist.png"),
                 x_label="SPL (dB)", title="Distribution of SPL in Data")
  plot_histogram(covered_num_tones,
                 os.path.join(plot_directory, "num_tones_hist.png"),
                 x_label="Num. tones in example",
                 title="Distribution of number of tones per example")
  plot_histogram(
      covered_frequencies,
      os.path.join(plot_directory, "covered_frequencies_hist.png"),
      bins=1000,
      logscale=True,
      x_label="frequency", title="Distribution over Frequencies")


def plot_heatmap(data: np.ndarray, path: str):
  """Plots and saves a heatmap of critical band co-occurrences."""
  fig, ax = plt.subplots()
  fig.set_size_inches(18.5, 18.5)
  # We want to show all ticks...
  ax.set_xticks(np.arange(data.shape[1]))
  ax.set_yticks(np.arange(data.shape[0]))
  # ... and label them with the respective list entries.
  labels = ["CB {}".format(i) for i in range(data.shape[1])]
  ax.set_xticklabels(labels)
  ax.set_yticklabels(labels)
  ax.set_title("Count per combination of Critical Bands in Examples")
  sns.heatmap(data, annot=True, fmt="d", xticklabels=labels, yticklabels=labels,
              ax=ax)
  plt.savefig(path)


def plot_average_num_tones(data: Dict[int, Dict[int, int]],
                           path: str):
  """Plots and saves a histogram of number of tones per example."""
  plt.subplots()
  all_bins = []
  all_counts = []
  for frequency_bin, counts in data.items():
    average = sum(
        [key * value for key, value in counts.items()]) / sum(
            [value for _, value in counts.items()])
    all_bins.append(frequency_bin)
    all_counts.append(average)
  plt.scatter(all_bins, all_counts)
  plt.savefig(path)


def write_examples(examples: List[List[str]],
                   file_name: str, path: str, example_ids=List[int],
                   seed=1) -> str:
  """Write tone-tone-set examples to csv."""
  random.seed(seed)
  # Get a random ordering and write the examples to a csv file in that order.
  example_order = list(range(len(examples)))
  random.shuffle(example_order)
  save_path = os.path.join(path, file_name + ".csv")
  with open(save_path, "wt") as infile:
    csv_writer = csv.writer(infile, delimiter=",")
    csv_writer.writerow(["id", "single_tone", "combined_tones"])
    with open(os.path.join(path, file_name + "_ids.csv"),
                    "w") as infile_ids:
      csv_writer_ids = csv.writer(infile_ids, delimiter=",")
      num_examples = 0
      for i in example_order:
        example = examples[i]
        example_id = example_ids[i]
        num_examples += 1
        csv_writer.writerow([num_examples, example[0], example[1]])

        # If the example is an ISO reproduction example save its ID in a
        # separate csv file.
        if example_id:
          csv_writer_ids.writerow([num_examples])
  return save_path


def write_data_specifications(data: Dict[str, Any],
                              file_name: str, path: str, plot: bool) -> str:
  """Write specifics of curves to make with a dataset."""
  save_path = os.path.join(path, file_name)
  with open(save_path, "w") as infile:
    curve_data = []
    for curve_representation, masker_curves in data.items():
      curve_representation = curve_representation.split(",")
      masker_frequency = curve_representation[0]
      probe_level = curve_representation[1]
      masker_probe_curve_data = {"masker_frequency": float(masker_frequency),
                                 "probe_level": int(probe_level),
                                 "curves": []}
      for masker_level, probe_freqs in masker_curves.items():
        masker_probe_curve_data["curves"].append({
            "masker_level":
                int(masker_level),
            "probe_frequencies":
                probe_freqs,
            "probe_masking": [
                [0]
                for _ in range(len(probe_freqs))
            ]
        })
      curve_data.append(masker_probe_curve_data)
    if plot:
      plot_masking_patterns(curve_data, path)
    json.dump(curve_data, infile, indent=4)
  return save_path


def save_two_tone_set(data: List[data_generation.ProbeMaskerPair],
                      iso_data: Dict[int, Dict[str, Any]],
                      critical_bands: List[int],
                      path: str, seed=1) -> Tuple[str, str, str, str]:
  """Combines two-tone and ISO data and plots data visualizations."""
  # Data structures for saving data and statitics about it.
  examples_probes = []

  # id of 1 will mean this example is an ISO repro example.
  example_ids_probes = []
  example_ids_maskers = []
  examples_maskers = []
  covered_levels_probes = []
  covered_levels_maskers = []
  covered_frequencies_probes = []
  covered_frequencies_maskers = []
  curves_probes = collections.defaultdict(
      lambda: collections.defaultdict(list))
  curves_maskers = collections.defaultdict(
      lambda: collections.defaultdict(list))
  cb_combinations_probes = np.zeros(
      [len(critical_bands) - 1,
       len(critical_bands) - 1], dtype=int)
  cb_combinations_maskers = np.zeros(
      [len(critical_bands) - 1,
       len(critical_bands) - 1], dtype=int)

  # Prepare the tuples of tones that each should make up two examples.
  for probe_masker_pair in data:
    masker_tone_level = probe_masker_pair.masker
    probe_tone_level = probe_masker_pair.probe
    masker_tone_representation = "[{},{}]".format(masker_tone_level.tone,
                                                  masker_tone_level.level)
    probe_tone_representation = "[{},{}]".format(probe_tone_level.tone,
                                                 probe_tone_level.level)

    # Find the corresponding critical band for visualization purposes
    cb_masker = data_generation.binary_search(critical_bands,
                                              masker_tone_level.tone)
    cb_probe = data_generation.binary_search(critical_bands,
                                             probe_tone_level.tone)
    cb_combinations_probes[cb_masker][cb_probe] += 1
    cb_combinations_maskers[cb_probe][cb_masker] += 1
    covered_levels_maskers.append(masker_tone_level.level)
    covered_levels_probes.append(probe_tone_level.level)
    covered_frequencies_maskers.append(masker_tone_level.tone)
    covered_frequencies_probes.append(probe_tone_level.tone)
    combined_representation = "[{},{}]".format(masker_tone_representation,
                                               probe_tone_representation)

    # Append two examples, one for each tone as the probe tone.
    examples_maskers.append(
        [masker_tone_representation, combined_representation])
    examples_probes.append([probe_tone_representation, combined_representation])

    # These examples are normal examples and not ISO standard reproduction ones.
    example_ids_probes.append(0)
    example_ids_maskers.append(0)

    # Append data statistics
    probe_curve_representation = "{},{}".format(masker_tone_level.tone,
                                                probe_tone_level.level)
    masker_curve_representation = "{},{}".format(probe_tone_level.tone,
                                                 masker_tone_level.level)
    curves_probes[probe_curve_representation][masker_tone_level.level].append(
        probe_tone_level.tone)
    curves_maskers[masker_curve_representation][probe_tone_level.level].append(
        masker_tone_level.tone)

  # Prepare the iso reproduction examples.
  for examples in iso_data.values():
    level = examples["ref1000_spl"]
    combined_tone_representation = "[[{},{}]]".format(1000, level)
    for other_tone in examples["other_tones"]:
      single_tone_representation = "[{},{}]".format(
          other_tone["frequency"], other_tone["level"])
      examples_probes.append([single_tone_representation,
                              combined_tone_representation])
      example_ids_probes.append(1)

  # Plot statistics on the data examples.
  plot_heatmap(cb_combinations_probes,
               os.path.join(path, "cb_heatmap_two_tone_set_probes.png"))
  plot_heatmap(cb_combinations_maskers,
               os.path.join(path, "cb_heatmap_two_tone_set_maskers.png"))
  plot_histogram(
      covered_levels_probes,
      os.path.join(path, "levels_hist_two_tone_set_probes.png"),
      x_label="dB (SPL)",
      title="Distribution over SPL")
  plot_histogram(
      covered_levels_maskers,
      os.path.join(path, "levels_hist_two_tone_set_maskers.png"),
      x_label="dB (SPL)",
      title="Distribution over SPL")
  plot_histogram(
      covered_frequencies_probes,
      os.path.join(path, "covered_frequencies_hist_two_tone_set_probes.png"),
      bins=1000,
      logscale=True,
      x_label="Frequency (Hz)",
      title="Distribution over frequency")
  plot_histogram(
      covered_frequencies_maskers,
      os.path.join(path, "covered_frequencies_hist_two_tone_set_maskers.png"),
      bins=1000,
      logscale=True,
      x_label="Frequency (Hz)",
      title="Distribution over frequency")
  probes_path = write_examples(examples_probes, "probes_two_tone_set", path,
                               example_ids_probes, seed=seed)
  maskers_path = write_examples(examples_maskers, "maskers_two_tone_set",
                                path, example_ids_maskers, seed=seed)
  probes_specs_path = write_data_specifications(
      curves_probes, "SPECS_probes_two_tone_set.json",
      path, plot=True)
  maskers_specs_path = write_data_specifications(
      curves_maskers, "SPECS_maskers_two_tone_set.json",
      path, plot=False)
  return probes_path, probes_specs_path, maskers_path, maskers_specs_path


def plot_iso_examples(data: Dict[int, Dict[str, Any]], path: str):
  """Plot ISO equal loudness curves w/ markers for the data examples."""
  _, ax = plt.subplots(1, 1, figsize=(12, 14))
  frequencies_on_range = [i for i in range(20, 20000, 10)]

  # These are the colors that will be used in the plot
  colors = [
      "#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c",
      "#98df8a", "#d62728", "#ff9896", "#9467bd", "#c5b0d5",
      "#8c564b", "#c49c94", "#e377c2", "#f7b6d2", "#7f7f7f",
      "#c7c7c7", "#bcbd22", "#dbdb8d", "#17becf", "#9edae5"]
  ax.set_prop_cycle(color=colors)
  plt.xscale("log")
  ax.set_xlabel("Frequency (Hz)")
  ax.set_ylabel("SPL (dB)")
  ax.set_title("ISO equal loudness curves")
  phons_levels = [i * 10 for i in range(10)]
  legend_handles = ["{} Phons".format(phons) for phons in phons_levels]
  levels_per_phons = []
  for phons in phons_levels:
    levels = []
    for frequency in frequencies_on_range:
      level = loudness.loudness_to_spl(phons, frequency)
      levels.append(level)
    levels_per_phons.append(levels)
  for i, y in enumerate(levels_per_phons):
    plt.plot(frequencies_on_range, y, label=legend_handles[i])

  for i, examples in enumerate(data.values()):
    level = examples["ref1000_spl"]
    plt.scatter(1000, level, marker="x", c="b")
    color = colors[i]
    for other_tone in examples["other_tones"]:
      if "error" in other_tone:
        plt.errorbar(other_tone["frequency"], other_tone["level"],
                     c=color, yerr=other_tone["error"], fmt="o")
      else:
        plt.scatter(other_tone["frequency"], other_tone["level"], marker="x",
                    c=color)
  ax.legend()
  plt.savefig(os.path.join(path, "iso_repro.png"))


def plot_masking_patterns(curves: List[Dict[str, Any]],
                          save_directory: str):
  """Plots the data in Zwicker-style."""
  for masker_freq_probe_level in curves:
    masker_frequency = masker_freq_probe_level["masker_frequency"]
    probe_level = masker_freq_probe_level["probe_level"]
    _, ax = plt.subplots(1, 1, figsize=(12, 14))
    ax.set_prop_cycle(color=[
        "#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c", "#98df8a",
        "#d62728", "#ff9896", "#9467bd", "#c5b0d5", "#8c564b", "#c49c94",
        "#e377c2", "#f7b6d2", "#7f7f7f", "#c7c7c7", "#bcbd22", "#dbdb8d",
        "#17becf", "#9edae5"
    ])
    plt.xscale("log")
    ax.set_xlabel("Probe Frequency (Hz)")
    ax.set_ylabel("Masked SPL (dB)")
    ax.set_title("Masker Frequency {}, Probe Level {}".format(
        masker_frequency, probe_level))
    plt.axvline(x=masker_frequency)
    plt.axhline(y=probe_level)
    for masker_curve in masker_freq_probe_level["curves"]:
      masker_level = masker_curve["masker_level"]
      frequencies = masker_curve["probe_frequencies"]
      masking = masker_curve["probe_masking"]
      average_masking = [np.mean(np.array(m)) for m in masking]
      std_masking = [np.std(np.array(m)) for m in masking]
      plt.errorbar(
          frequencies,
          average_masking,
          yerr=std_masking,
          fmt="o",
          label="Masker Level {}".format(masker_level))
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels)
    plt.savefig(os.path.join(save_directory,
                             "masker_{}_probe_{}.png".format(
                                 masker_frequency, probe_level)))


def save_iso_reproduction_examples(data: Dict[int, Dict[str, Any]], path: str):
  """Save the ISO reproduction examples in a csv file."""
  with open(os.path.join(path, "data_iso_repro.csv"), "w") as infile:
    csv_writer = csv.writer(infile, delimiter=",")
    csv_writer.writerow(["id", "single_tone", "combined_tones"])
    num_examples = 0
    for _, examples in data.items():
      level = examples["ref1000_spl"]
      combined_tone_representation = "[[{},{}]]".format(1000, level)
      for other_tone in examples["other_tones"]:
        num_examples += 1
        single_tone_representation = "[{},{}]".format(
            other_tone["frequency"], other_tone["level"])
        csv_writer.writerow([num_examples, single_tone_representation,
                             combined_tone_representation])


def save_data(data: Dict[int, List[Dict[str, List[int]]]], path: str,
              critical_bands: List[int]) -> Tuple[Dict[int, Any], int, int]:
  """Save the dataset with a different number of tones in examples.

  Args:
    data: the data generated by data_generation.generate_data
    path: a path where the dataset should be saved
    critical_bands:  the boundaries of each cb are at index i and i + 1

  Returns:
    Data for making a histogram of number of tones per critical band,
    the number of unique examples, and the number of total examples.
    The difference being that each unique example is shown twice with a
    different probe tone.
  """
  # Some structures to keep track of data statistics.
  total_unique_examples = 0
  total_num_examples_listeners = 0
  covered_frequencies = []
  covered_phons = []
  covered_levels = []
  covered_num_tones = []
  covered_num_tones_per_cb = collections.defaultdict(
      lambda: collections.defaultdict(int))
  _ = collections.defaultdict(
      lambda: collections.defaultdict(int))
  cb_combinations = np.zeros([len(critical_bands) - 1, len(critical_bands) - 1],
                             dtype=int)

  # Go over the data and save it in the right format in a csv file.
  with open(os.path.join(path, "data.csv"), "w") as infile:
    csv_writer = csv.writer(infile, delimiter=",")
    csv_writer.writerow(["id", "single_tone", "combined_tones"])
    for num_tones, examples in data.items():
      for example in examples:
        covered_num_tones.append(num_tones)
        total_unique_examples += 1
        frequencies = example["frequencies"]
        levels = example["levels"]
        phons = example["phons"]
        covered_phons.extend(phons)
        current_critical_bands = []
        combined_tone_representation = []
        for frequency, level in zip(frequencies, levels):
          combined_tone_representation.append("[{},{}]".format(frequency,
                                                               level))
        combined_tone_representation = ",".join(combined_tone_representation)
        combined_tone_representation = "[" + combined_tone_representation + "]"
        for frequency, level in zip(frequencies, levels):
          total_num_examples_listeners += 1
          csv_writer.writerow([total_num_examples_listeners,
                               "[{},{}]".format(frequency, level),
                               combined_tone_representation])
          cb = data_generation.binary_search(critical_bands, frequency)
          covered_num_tones_per_cb[cb][num_tones] += 1
          current_critical_bands.append(cb)
          covered_frequencies.append(frequency)
          covered_levels.append(level)
        for cb_1, cb_2 in itertools.combinations(current_critical_bands, r=2):
          cb_combinations[cb_1][cb_2] += 1
          cb_combinations[cb_2][cb_1] += 1
  plot_histograms(path, covered_frequencies, covered_phons, covered_num_tones,
                  covered_levels)
  plot_heatmap(cb_combinations, os.path.join(path, "cb_heatmap.png"))
  return (covered_num_tones_per_cb, total_unique_examples,
          total_num_examples_listeners)


def plot_loudness_conversion(path: str, phons_levels: List[int],
                             frequencies: List[int]):
  """PLot ISO loudness curves with loudness to decibel conversion."""
  _, ax = plt.subplots(1, 1, figsize=(12, 14))

  # These are the colors that will be used in the plot
  ax.set_prop_cycle(color=[
      "#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c",
      "#98df8a", "#d62728", "#ff9896", "#9467bd", "#c5b0d5",
      "#8c564b", "#c49c94", "#e377c2", "#f7b6d2", "#7f7f7f",
      "#c7c7c7", "#bcbd22", "#dbdb8d", "#17becf", "#9edae5"])
  plt.xscale("log")
  levels_per_phons = []
  for phons in phons_levels:
    levels = []
    for frequency in frequencies:
      level = loudness.loudness_to_spl(phons, frequency)
      levels.append(level)
    levels_per_phons.append(levels)
  for y in levels_per_phons:
    plt.plot(frequencies, y)
  plt.savefig(path)


def plot_beatrange(path: str):
  plt.subplots(1, 1, figsize=(12, 14))
  x = [20 + i * 1000 for i in range(20)]
  y = [data_generation.calculate_beat_range(frequency) for frequency in x]
  plt.plot(x, y, marker="o")
  plt.savefig(path)
