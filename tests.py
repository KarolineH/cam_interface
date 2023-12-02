from capture import EOS
import gphoto_util
import time
import numpy as np


cam1 = EOS()
tests = 25

# Test 1: Get aperture value
# 01.12.2023 at Zinc, PHOTO mode: avg over 25 tests: 0.0000196s
# 02.12.2023 at bo, PHOTO mode: avg over 25 tests: 0.00002721s
results = []
for i in range(tests):
    start = time.time()
    val, choices, msg = cam1.set_aperture(list_choices=True)
    end = time.time()
    results.append(end-start)
avg_latency = np.mean(np.asarray(results))
print("Average latency: ", avg_latency)

# Test 2: Set aperture
# 01.12.2023 at Zinc, PHOTO mode: avg over 25 tests: 0.0043
# 02.12.2023 at bo, PHOTO mode: avg over 25 tests: 0.00119
vals = [2.8, 32] # smallest and largest aperture values to flick between
results = []
for i in range(tests):
    val = vals[i%2]
    start = time.time()
    val, choices, msg = cam1.set_aperture(val)
    end = time.time()
    results.append(end-start)
avg_latency = np.mean(np.asarray(results))
print("Average latency: ", avg_latency)


# Test 3: Get shutter speed value
# 01.12.2023 at Zinc, PHOTO mode: avg over 25 tests: 0.00130
# 02.12.2023 at bo, PHOTO mode: avg over 25 tests: 0.0003124
results = []
for i in range(tests):
    start = time.time()
    val, choices, msg = cam1.set_shutterspeed(list_choices=True)
    end = time.time()
    results.append(end-start)
avg_latency = np.mean(np.asarray(results))
print("Average latency: ", avg_latency)


# Test 4: Set shutter speed
# 01.12.2023 at Zinc, PHOTO mode: avg over 25 tests: 0.00554
# 02.12.2023 at bo, PHOTO mode: avg over 25 tests: 0.004445
vals = [30, 1/8000] # smallest and largest shutter speed values to flick between
results = []
for i in range(tests):
    val = vals[i%2]
    start = time.time()
    val, choices, msg = cam1.set_shutterspeed(val)
    end = time.time()
    results.append(end-start)
avg_latency = np.mean(np.asarray(results))
print("Average latency: ", avg_latency)
print('done')