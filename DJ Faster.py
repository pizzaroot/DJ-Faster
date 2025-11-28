import random, requests, json, os, ffmpeg, audioread
import numpy as np

def constant_acceleration_map(t_input, T_in, pct_start, pct_end):
    r0 = 1.0 + pct_start / 100.0
    r1 = 1.0 + pct_end / 100.0

    if abs(r1 - r0) < 1e-9:
        return t_input / r0

    a_term = (r1**2 - r0**2) / (2.0 * T_in)
  
    discriminant = r0**2 + 4.0 * (0.5 * a_term) * t_input

    t_out = (-r0 + np.sqrt(r0**2 + 2.0 * a_term * t_input)) / a_term
    
    return t_out

x = requests.get('http://localhost:24050/json')
data = x.json()

filename = data["settings"]["folders"]["songs"] + "\\" + data["menu"]["bm"]["path"]["folder"] + "\\" + data["menu"]["bm"]["path"]["file"]
start_pct = float(input("Start rate: "))
end_pct = float(input("Final rate: "))

r0 = 1.0 + start_pct / 100.0
r1 = 1.0 + end_pct / 100.0

def get(t):
    return int(constant_acceleration_map((t / 1000), T_input, start_pct, end_pct) * 1000)

f = open(filename, mode="r", encoding="utf-8")

for line in f.readlines():
    if line.startswith("AudioFilename:"):
        audiofilename = line[15:-1]
       
f.close()


original_audio_path = os.path.dirname(filename) + '\\' + audiofilename
T_input = 0

with audioread.audio_open(original_audio_path) as ff:
    T_input = ff.duration

dap = ""
dap2 = ""

f = open(filename, mode="r", encoding="utf-8")
started = 0
audiofilename = "audio.mp3"

timingpoints = []


def get_rate_at(t):
    return r0 + t / 1000 / T_input * (r1 - r0)

for line in f.readlines():
    if started == 2 and line != '\n':
        tmp = line.split(':')
        tmp2 = tmp[0].split(",")

        tmp2[2] = str(get(int(tmp2[2])))
        tmp2[5] = str(get(int(tmp2[5])))
        tmp[0] = ",".join(tmp2)
        dap2 += ":".join(tmp)
    elif started == 1 and line != '\n' and not line.startswith('['):
        tmp = line.split(",")
        if not tmp[1].startswith('-'):
            timingpoints.append([int(tmp[0]), float(tmp[1])])
            tmp[1] = str(float(tmp[1]) / get_rate_at(int(tmp[0])))
        elif len(timingpoints) > 0:
            tmp[1] = str(-100 * timingpoints[0][1] / timingpoints[-1][1] * get_rate_at(int(tmp[0])) / r0)
        else:
            tmp[1] = str(-100 * get_rate_at(int(tmp[0])) / r0) 
        tmp[0] = str(get(int(tmp[0])))
        dap2 += ",".join(tmp)
    else:
        if line.startswith("Version:"):
            dap += line[:-1] + " [faster]\n"
        elif line.startswith("AudioFilename:"):
            dap += "AudioFilename: audio (faster).mp3\n"
            audiofilename = line[15:-1]
        elif line.startswith("PreviewTime:"):
            dap += f"PreviewTime: {str(get(int(line[13:-1])))}\n"
        elif started == 0:
            dap += line
        else:
            dap2 += line
    if line.startswith("[HitObjects]"):
        started += 1
    if line.startswith("[TimingPoints]"):
        started += 1
       
f.close()

curtime = timingpoints[0][0]
curinterval = timingpoints[0][1]
nxtidx = 1

while curtime < T_input * 1000:
    if nxtidx >= len(timingpoints) or curtime + curinterval < timingpoints[nxtidx][0]:
        curtime += curinterval
        dap += str(int(get(curtime))) + ',' + str(curinterval / get_rate_at(curtime)) + ",4,2,1,100,1,0\n"
        dap += str(int(get(curtime))) + ',' + str(-100 * timingpoints[0][1] / curinterval * get_rate_at(curtime) / r0) + ",4,2,1,100,0,0\n"
    else:
        curtime = timingpoints[nxtidx][0]
        curinterval = timingpoints[nxtidx][1]
        nxtidx += 1
    
    

f = open(filename[:-5] + " [faster]].osu", mode="w", encoding="utf-8")
f.write(dap + dap2)
f.close()

import pipeclient

client = pipeclient.PipeClient()
client.write("SelAllTracks:")
client.write("RemoveTracks:")
client.write("Import2: Filename=\"" + (os.path.dirname(filename) + '\\' + audiofilename) + "\"")
client.write("SelectAll:")
client.write(f"SlidingStretch: RatePercentChangeStart={start_pct} RatePercentChangeEnd={end_pct}")
client.write("SelectAll:")
client.write(f"Export2: Filename=\"{os.path.dirname(filename)}\\audio (faster).mp3\" NumChannels=2")

client.write("SelAllTracks:")
client.write("RemoveTracks:")
