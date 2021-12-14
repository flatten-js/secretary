import argparse
import datetime
import os
import shutil
import subprocess
import sys
import time

import ffmpeg
import spacy
import speech_recognition as sr
import tqdm

parser = argparse.ArgumentParser()

parser.add_argument('-i', '--input', default = './data')
parser.add_argument('-o', '--output', default = './output')

args = parser.parse_args()


class Secretary:
    def __init__(self, output):
        self.output = output
        self.output_path = self.__output_path(output)
        self.recognizer = sr.Recognizer()
        self.nlp = spacy.load('ja_ginza')

    def __output_path(self, output):
        path = os.path.join(output, self.__now())
        os.mkdir(path)
        return path

    def __now(self):
        now = datetime.datetime.now()
        return now.strftime('%Y%m%d%H%M%S')

    def __file_size(self, filename):
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout = result.stdout
        return 0 if b'N/A' in stdout else float(stdout)

    def movie_to_audio(self, input_path, output_path):
        name, ext = os.path.splitext(os.path.basename(input_path))

        stream = ffmpeg.input(input_path)
        _duration = 60
        _start = 0
        audio = { 'name': name, 'list': [] }
        while True:
            filename = os.path.join(output_path, f'{name}.{_start}.wav')

            start = _duration * _start
            time_range = { 'start': start, 'end': start + _duration if start else _duration }
            stream_trim = stream.audio.filter('atrim', **time_range)

            stream_output = ffmpeg.output(stream_trim, filename)
            ffmpeg.run(stream_output, quiet = True)

            size = self.__file_size(filename)
            if not size: break

            audio['list'].append(filename)
            _start += 1

        return audio

    def audio_to_text(self, filename):
        with sr.AudioFile(filename) as source:
            audio = self.recognizer.record(source)
        return self.recognizer.recognize_google(audio, language = 'ja-JP')

    def save_text(self, name, text):
        path = os.path.join(self.output_path, f'{name}.txt')
        with open(path, 'a', encoding = 'utf-8') as f: f.write(text)

    def text_build(self, text):
        # text = text.replace(' ', '')
        doc = self.nlp(text)
        return '\n'.join(map(str, doc.sents))

    def __write(self, input, output_path):
        for filename in tqdm.tqdm(os.listdir(input)):
            input_path = os.path.join(input, filename)

            audio = self.movie_to_audio(input_path, output_path)
            for audio_filename in tqdm.tqdm(audio['list'], leave = False):
                try:
                    text = self.audio_to_text(audio_filename)
                    text = self.text_build(text)
                    print('text: ', text)
                    self.save_text(audio['name'], text)
                except Exception as e:
                    print(e)
                    # pass

    def write(self, input):
        output_path = os.path.join(self.output_path, 'tmp')
        if os.path.isdir(output_path): shutil.rmtree(output_path)
        os.mkdir(output_path)

        try:
            self.__write(input, output_path)
        finally:
            shutil.rmtree(output_path)


if __name__ == '__main__':
    secretary = Secretary(args.output)
    secretary.write(args.input)
