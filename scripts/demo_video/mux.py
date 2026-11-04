import json, subprocess, sys
V = sys.argv[1]; c = json.load(open(f"{V}/cues.json")); total = c["t_end"] - c["t0"]
inputs, filt, labels = [], [], []
for i, q in enumerate(c["cues"]):
    inputs += ["-i", f"{V}/audio/{q['key']}.aiff"]
    ch = f"[{i+1}:a]aresample=48000,aformat=channel_layouts=stereo"
    if q["trim"]: ch += f",atrim=0:{q['trim']},afade=t=out:st={q['trim']-0.8}:d=0.8"
    ch += f",adelay={int(q['t']*1000)}:all=1[a{i}]"
    filt.append(ch); labels.append(f"[a{i}]")
filt.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,apad,atrim=0:{total:.2f},loudnorm=I=-16:TP=-1.5[aout]")
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{V}/frames.txt", *inputs,
       "-filter_complex", ";".join(filt) + ";[0:v]fps=30,format=yuv420p[vout]", "-map", "[vout]", "-map", "[aout]",
       "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
       "-t", f"{total:.2f}", f"{V}/nunchi-demo.mp4"]
subprocess.run(cmd, check=True); print("ok", round(total, 1))
