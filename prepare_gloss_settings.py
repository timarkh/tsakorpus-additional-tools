import os
import shutil
import re
import json
from lxml import etree
import argparse


class GlossCollector:
    """
    A class for collecting all glosses and part-of-speech tags from
    a corpus. Different file types are processed by different subclasses.
    """
    rxBadGlosses = re.compile('^(?:I|[0-9]{2,})$')

    def __init__(self, posTierType='', glossTierType='',
                 lang='', ext='', corpusDir='.'):
        self.posTierType = posTierType
        self.glossTierType = glossTierType
        self.lang = lang      # language name as in the settings files
        self.posTags = {}     # POS tag -> frequency
        self.glosses = {}     # gloss -> frequency
        self.ext = ext        # file extension for corpus files
        if len(ext) > 0 and not ext.startswith('.'):
            ext = '.' + ext
        self.corpusDir = corpusDir
        self.tags2cat = {}
        fIn = open('data/common_gramm_tags.json', 'r', encoding='utf-8')
        self.tags2cat = json.load(fIn)
        fIn.close()

    def get_glosses(self, data):
        """
        Return all glosses extracted from the contents of one file (data)
        together with their frequencies.
        Implemented in subclasses.
        """
        return {}

    def get_pos_tags(self, data):
        """
        Return all POS tags extracted from the contents of one file (data)
        together with their frequencies.
        Implemented in subclasses.
        """
        return {}

    def load_file(self, fname):
        """
        Return the contents of one corpus file.
        Should be overriden in subclasses.
        """
        fIn = open(fname, 'r', encoding='utf-8')
        data = fIn.read()
        fIn.close()
        return data

    def process_file(self, fname):
        """
        Walk over the corpus directory, look into each suitable file
        and add its glosses and POS tags to the list.
        """
        data = self.load_file(fname)
        curPosTags = self.get_pos_tags(data)
        for pos in curPosTags:
            try:
                self.posTags[pos] += curPosTags[pos]
            except KeyError:
                self.posTags[pos] = curPosTags[pos]
        curGlosses = self.get_glosses(data)
        for gloss in curGlosses:
            try:
                self.glosses[gloss] += curGlosses[gloss]
            except KeyError:
                self.glosses[gloss] = curGlosses[gloss]

    def process_corpus(self):
        """
        Walk over the corpus directory, look into each suitable file
        and add information about its glosses and POS tags to the dictionaries.
        """
        nFiles = 0
        for root, dirs, files in os.walk(self.corpusDir):
            for fname in files:
                if not fname.lower().endswith(self.ext):
                    continue
                self.process_file(os.path.join(root, fname))
                nFiles += 1
        self.glosses = {gl: self.glosses[gl] for gl in self.glosses
                        if self.rxBadGlosses.search(gl) is None}
        print('Corpus processed, ' + str(nFiles) + ' files in total.')
        print(str(len(self.glosses)) + ' unique glosses, ' + str(len(self.posTags))
              + ' unique POS tags collected.')

    def prepare_settings_files(self):
        """
        After processing the corpus, generate the settings files
        needed for tsakorpus JSON conversion, as well as a short report.
        """
        glossList = [gl for gl in self.glosses]
        glossList.sort()
        convSettingsFname = os.path.join(self.corpusDir, 'conversion_settings.json')
        settings = {}
        if os.path.exists(convSettingsFname):
            backupFname = convSettingsFname + '.bak'
            shutil.copy2(convSettingsFname, backupFname)
            fIn = open(convSettingsFname, 'r', encoding='utf-8')
            settings = json.load(fIn)
            fIn.close()
        settings['glosses'] = glossList
        fOut = open(convSettingsFname, 'w', encoding='utf-8')
        json.dump(settings, fOut, indent=4, ensure_ascii=False, sort_keys=True)
        fOut.close()

        fOut = open(os.path.join(self.corpusDir, 'grammRules.csv'), 'w', encoding='utf-8')
        for gloss in glossList:
            fOut.write(gloss + '\t' + gloss.lower().replace('.', ',') + '\n')
        fOut.close()

        fOut = open(os.path.join(self.corpusDir, 'glosses.html'), 'w', encoding='utf-8')
        fOut.write('<html><head><title>Glosses and POS for ' + self.lang + '</title></head>\n<body>')
        fOut.write('<h1>Glosses</h1>\n<table>')
        for gloss in sorted(self.glosses, key=lambda x: (-self.glosses[x], x)):
            fOut.write('<tr><td>' + gloss + '</td><td>' + str(self.glosses[gloss]) + '</td></tr>\n')
        fOut.write('</table>\n<h1>POS</h1>\n<table>')
        for pos in sorted(self.posTags, key=lambda x: (-self.posTags[x], x)):
            fOut.write('<tr><td>' + pos + '</td><td>' + str(self.posTags[pos]) + '</td></tr>\n')
        fOut.close()

        categories = {self.lang: {}}
        for pos in self.posTags:
            categories[self.lang][pos] = 'pos'
        for gloss in glossList:
            for tag in re.split('[/.]', gloss.lower()):
                if tag in self.posTags:
                    continue    # do not overwrite POS tags as they are more essential for the search
                cat = 'add'
                if tag in self.tags2cat:
                    cat = self.tags2cat[tag]
                categories[self.lang][tag] = cat

        fOut = open(os.path.join(self.corpusDir, 'categories.json'), 'w', encoding='utf-8')
        json.dump(categories, fOut, indent=4, ensure_ascii=False, sort_keys=True)
        fOut.close()

        corpusSettings = {'lang_props': {self.lang:
                                             {'gloss_shortcuts': {},
                                              'gloss_selection': {'columns': []},
                                              'gramm_selection': {'columns': []}}}}

    def run(self):
        """
        The main function that calls all necessary procedures in turn.
        """
        self.process_corpus()
        self.prepare_settings_files()


class ISOTEIGlossCollector(GlossCollector):
    """
    A subclass of GlossCollector for Hamburg ISO/TEI files.
    """
    namespaces = {'tei': 'http://www.tei-c.org/ns/1.0',
                  'xml': 'http://www.w3.org/XML/1998/namespace'}

    def get_glosses(self, data):
        """
        Return all glosses extracted from the contents of one file (data)
        together with their frequencies.
        """
        curGlosses = {}
        annotations = data.xpath('/tei:TEI/tei:text/tei:body/tei:annotationBlock',
                                 namespaces=self.namespaces)
        for anno in annotations:
            for tier in anno.xpath('tei:spanGrp',
                                   namespaces=self.namespaces):
                if 'type' not in tier.attrib:
                    continue
                tierID = tier.attrib['type']
                if tierID != self.glossTierType:
                    continue
                for wSpan in tier:
                    for mSpan in wSpan:
                        if mSpan.text is not None and len(mSpan.text) > 0 and mSpan.text.upper() == mSpan.text:
                            gloss = mSpan.text
                            try:
                                curGlosses[gloss] += 1
                            except KeyError:
                                curGlosses[gloss] = 1
        return curGlosses

    def get_pos_tags(self, data):
        """
        Return all POS tags extracted from the contents of one file (data)
        together with their frequencies.
        Implemented in subclasses.
        """
        curPOS = {}
        annotations = data.xpath('/tei:TEI/tei:text/tei:body/tei:annotationBlock',
                                 namespaces=self.namespaces)
        for anno in annotations:
            for tier in anno.xpath('tei:spanGrp',
                                   namespaces=self.namespaces):
                if 'type' not in tier.attrib:
                    continue
                tierID = tier.attrib['type']
                if tierID != self.posTierType:
                    continue
                for wSpan in tier:
                    if wSpan.text is not None and len(wSpan.text) > 0:
                        pos = wSpan.text
                        try:
                            curPOS[pos] += 1
                        except KeyError:
                            curPOS[pos] = 1
        return curPOS

    def load_file(self, fname):
        """
        Return the contents of one corpus file.
        Should be overriden in subclasses.
        """
        data = etree.parse(fname)
        return data


class ExmaraldaGlossCollector(GlossCollector):
    """
    A subclass of GlossCollector for Hamburg Exmaralda (exb) files.
    """

    def get_glosses(self, data):
        """
        Return all glosses extracted from the contents of one file (data)
        together with their frequencies.
        """
        curGlosses = {}
        for tier in data.xpath('/basic-transcription/basic-body/tier[@type=\'a\']'):
            if 'category' not in tier.attrib:
                continue
            tierID = tier.attrib['category']
            if tierID != self.glossTierType:
                continue
            for wSpan in tier:
                if wSpan.text is not None and len(wSpan.text) > 0:
                    for gloss in re.split('[-=]|\\.\\[', wSpan.text):
                        gloss = gloss.strip('[]()<>')
                        if gloss != gloss.upper():
                            continue
                        try:
                            curGlosses[gloss] += 1
                        except KeyError:
                            curGlosses[gloss] = 1
        return curGlosses

    def get_pos_tags(self, data):
        """
        Return all POS tags extracted from the contents of one file (data)
        together with their frequencies.
        Implemented in subclasses.
        """
        curPOS = {}
        for tier in data.xpath('/basic-transcription/basic-body/tier[@type=\'a\']'):
            if 'category' not in tier.attrib:
                continue
            tierID = tier.attrib['category']
            if tierID != self.posTierType:
                continue
            for wSpan in tier:
                if wSpan.text is not None and len(wSpan.text) > 0:
                    pos = wSpan.text
                    try:
                        curPOS[pos] += 1
                    except KeyError:
                        curPOS[pos] = 1
        return curPOS

    def load_file(self, fname):
        """
        Return the contents of one corpus file.
        Should be overriden in subclasses.
        """
        data = etree.parse(fname)
        return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Collect glosses and POS tags from a corpus and'
                                                 ' prepare tsakorpus settings files based on this list.')
    parser.add_argument('-f', '--format', help='Corpus format (tei/exb/eaf)',
                        default='tei')
    parser.add_argument('-l', '--lang', help='Language name',
                        default='')
    parser.add_argument('--dir', help='Path to the corpus',
                        default='.')
    parser.add_argument('--pos', help='POS tier type',
                        default='ps')
    parser.add_argument('--gloss', help='Gloss tier type',
                        default='ge')
    args = parser.parse_args()
    if args.format == 'tei':
        gc = ISOTEIGlossCollector(posTierType=args.pos,
                                  glossTierType=args.gloss,
                                  lang=args.lang,
                                  corpusDir=args.dir,
                                  ext='xml')
        gc.run()
    elif args.format == 'exb':
        gc = ExmaraldaGlossCollector(posTierType=args.pos,
                                     glossTierType=args.gloss,
                                     lang=args.lang,
                                     corpusDir=args.dir,
                                     ext='exb')
        gc.run()
    else:
        print('Only ISO/TEI xml and EXMARaLDA exb are supported at the moment.')
