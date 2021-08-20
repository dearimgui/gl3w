#!/usr/bin/env python

#   This file is part of gl3w, hosted at https://github.com/skaslev/gl3w
#
#   This is free and unencumbered software released into the public domain.
#
#   Anyone is free to copy, modify, publish, use, compile, sell, or
#   distribute this software, either in source code form or as a compiled
#   binary, for any purpose, commercial or non-commercial, and by any
#   means.
#
#   In jurisdictions that recognize copyright laws, the author or authors
#   of this software dedicate any and all copyright interest in the
#   software to the public domain. We make this dedication for the benefit
#   of the public at large and to the detriment of our heirs and
#   successors. We intend this dedication to be an overt act of
#   relinquishment in perpetuity of all present and future rights to this
#   software under copyright law.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#   EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#   MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#   IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
#   OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#   ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#   OTHER DEALINGS IN THE SOFTWARE.

# Allow Python 2.6+ to use the print() function
from __future__ import print_function

import argparse
import os
import re

# Try to import Python 3 library urllib.request
# and if it fails, fall back to Python 2 urllib2
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

EXT_SUFFIX = ['ARB', 'EXT', 'KHR', 'OVR', 'NV', 'AMD', 'INTEL']

def is_ext(proc):
    return any(proc.endswith(suffix) for suffix in EXT_SUFFIX)

def write(f, s):
    f.write(s.encode('utf-8'))

def touch_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def download(url, dst):
    if os.path.exists(dst):
        print('Reusing {0}...'.format(dst))
        return

    print('Downloading {0}...'.format(dst))
    web = urllib2.urlopen(url)
    with open(dst, 'wb') as f:
        f.writelines(web.readlines())

parser = argparse.ArgumentParser(description='gl3w generator script')
parser.add_argument('--ext', action='store_true', help='Load extensions')
parser.add_argument('--root', type=str, default='', help='Root directory')
args = parser.parse_args()

# Create directories
touch_dir(os.path.join(args.root, 'include/GL'))
touch_dir(os.path.join(args.root, 'include/KHR'))
touch_dir(os.path.join(args.root, 'src'))

# Download glcorearb.h and khrplatform.h
download('https://www.khronos.org/registry/OpenGL/api/GL/glcorearb.h',
         os.path.join(args.root, 'include/GL/glcorearb.h'))
download('https://www.khronos.org/registry/EGL/api/KHR/khrplatform.h',
         os.path.join(args.root, 'include/KHR/khrplatform.h'))

# Parse function names from glcorearb.h
print('Parsing glcorearb.h header...')
procs = []
p = re.compile(r'GLAPI.*APIENTRY\s+(\w+)')
with open(os.path.join(args.root, 'include/GL/glcorearb.h'), 'r') as f:
    for line in f:
        m = p.match(line)
        if not m:
            continue
        proc = m.group(1)
        if args.ext or not is_ext(proc):
            procs.append(proc)
procs.sort()

# Generate gl3w.h
print('Generating {0}...'.format(os.path.join(args.root, 'include/GL/gl3w.h')))
with open(os.path.join(args.root, 'include/GL/gl3w.h'), 'wb') as f:
    gl3w_h = open(os.path.join(args.root, 'template/gl3w.h'), 'r', encoding='utf-8').read()
    strings = [
        '/* gl3w internal state */',
        'union GL3WProcs {',
        '\tGL3WglProc ptr[{0}];'.format(len(procs)),
        '\tstruct {'
    ]
    for proc in procs:
        strings.append('\t\t{0: <55} {1};'.format('PFN{0}PROC'.format(proc.upper()), proc[2:]))
    strings.append('\t} gl;')     # struct
    strings.append('};')            # union GL3WProcs
    gl3w_h = gl3w_h.replace(strings[0], '\n'.join(strings))

    strings = ['/* OpenGL functions */']
    for proc in procs:
        strings.append('#define {0: <48} gl3wProcs.gl.{1}'.format(proc, proc[2:]))
    gl3w_h = gl3w_h.replace(strings[0], '\n'.join(strings))
    write(f, gl3w_h)

# Generate gl3w.c
print('Generating {0}...'.format(os.path.join(args.root, 'src/gl3w.c')))
with open(os.path.join(args.root, 'src/gl3w.c'), 'wb') as f:
    gl3w_c = open(os.path.join(args.root, 'template/gl3w.c'), 'r', encoding='utf-8').read()
    strings = ['static const char *proc_names[] = {']
    for proc in procs:
        strings.append('\t"{0}",'.format(proc))
    gl3w_c = gl3w_c.replace(strings[0], '\n'.join(strings))
    write(f, gl3w_c)
