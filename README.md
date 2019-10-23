tsakorpus-additional-tools
==========================

A set of tools for data preprocessing or settings file generation for [tsakorpus](https://bitbucket.org/tsakorpus/tsakorpus/).

# prepare_gloss_settings

A tool that collects glosses and POS tags used in the corpus and generates a report and settings files: conversion_settings.json, categories.json, and grammRules.csv (tab-delimited). All files are generated in the corpus directory. If conversion_settings.json is already present there, it is copied to conversion_settings.json.bak, and then updated. It is presumed that the generated files are further processed manually by a linguist, who should remove erroneously collected glosses, adjust the gloss-to-tag rules, etc.

## Usage

Command line examples:

* ``python prepare_gloss_settings.py -f tei --dir C:\Work\HZSK\corpora\selkup_tei -l selkup --pos ps --gloss ge``
* ``python prepare_gloss_settings.py -f exb --dir C:\Work\HZSK\corpora\selkup -l selkup --pos ps --gloss ge``

(use ``python3`` if you have also Python 2 installed)

Type ``python prepare_gloss_settings.py -h`` for help.

## Requirements

The tools require the following software to run:

* python >= 3.5
* python modules: lxml (you can use requirements.txt)


## License

The software is distributed under MIT license (see LICENSE.md).
