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
import os.path
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
    web = urllib2.urlopen(urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0'}))
    with open(dst, 'wb') as f:
        f.writelines(web.readlines())


class IfDefNode(object):
    def __init__(self, parent=None):
        self.children = []
        self.parent = parent
        if parent is not None:
            parent.children.append(self)

    def __str__(self):
        if len(self.children):
            return str(self.children[0])
        return '<empty>'


def cull_empty(node):
    new_children = []
    for c in node.children:
        if isinstance(c, str) or cull_empty(c):
            new_children.append(c)
    node.children = new_children
    return len(node.children) > 2


def gather_children(node):
    for c in node.children:
        if isinstance(c, str):
            yield c
        else:
            yield from gather_children(c)


def main():
    script_dir = os.path.dirname(__file__)
    parser = argparse.ArgumentParser(description='gl3w generator script')
    parser.add_argument('--ext', action='store_true', help='Load extensions')
    parser.add_argument('--root', type=str, default='', help='Root directory')
    parser.add_argument('--ref', nargs='+', default=[], help='Scan files or dirs and only include used APIs.')
    parser.add_argument('--output', default='include/GL/imgui_impl_opengl3_loader.h', help='Output header.')
    args = parser.parse_args()

    # Create symbol whitelist
    re_fun = re.compile(r'\b(gl[A-Z][a-zA-Z0-9_]+)\b')
    re_def = re.compile(r'\b(GL_[a-zA-Z0-9_]+)\b')
    re_comments = re.compile(r'//.*?\n|/\*.*?\*/', re.MULTILINE | re.DOTALL)
    whitelist = set()

    # Include extensions, they will be trimmed if unused anyway.
    args.ext = args.ext or len(args.ref)
    for api_ref in args.ref:
        with open(api_ref) as fp:
            source_code = fp.read()
            # Avoid including unused symbols that may appear in comments.
            source_code = re_comments.sub('', source_code)
            for e in re_def.findall(source_code):
                whitelist.add(e)
            for e in re_fun.findall(source_code):
                whitelist.add(e)
                whitelist.add('PFN{}PROC'.format(e.upper()))

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
    d = re.compile(r'#define\s+(GL_[a-zA-Z0-9_]+)\s+(0x)?[0-9A-F]+')
    f = re.compile(r'\bAPIENTRYP (PFNGL[A-Z0-9]+PROC)\b')
    glcorearb = IfDefNode()
    with open(os.path.join(args.root, 'include/GL/glcorearb.h'), 'r') as fp:
        for line in fp:
            # Match API
            m = p.match(line)
            if m is not None:
                proc = m.group(1)
                if (args.ext or not is_ext(proc)) and len(whitelist) == 0 or proc in whitelist:
                    procs.append(proc)
                else:
                    continue

            # Exclude non-whitelisted preprocessor definitions
            m = d.match(line)
            if m is not None and len(whitelist) and m.group(1) not in whitelist:
                continue

            # Exclude non-whitelisted function pointer types
            m = f.search(line)
            if m is not None and len(whitelist) and m.group(1) not in whitelist:
                continue

            line = line.rstrip('\r\n')
            if line.startswith('#if'):
                glcorearb = IfDefNode(glcorearb)
                glcorearb.children.append(line)
            elif line.startswith('#endif'):
                glcorearb.children.append(line)
                glcorearb = glcorearb.parent
            elif line:
                glcorearb.children.append(line)
    procs.sort()
    assert glcorearb.parent is None
    cull_empty(glcorearb)                               # Walk parsed glcorearb and cull empty ifdefs
    glcorearb = '\n'.join(gather_children(glcorearb))   # Reassemble glcorearb.h

    # Generate gl3w.h
    print('Generating {0}...'.format(args.output))
    with open(args.output, 'w+', encoding='utf-8') as fp:
        h_template = open('{}/template/gl3w.h'.format(script_dir)).read()

        strings = [
            '/* gl3w internal state */',
            'union GL3WProcs {',
            '    GL3WglProc ptr[{0}];'.format(len(procs)),
            '    struct {'
        ]
        max_proc_len = max([len(p) for p in procs]) + 7
        for proc in procs:
            strings.append('        {0: <{2}} {1};'.format('PFN{0}PROC'.format(proc.upper()), proc[2:], max_proc_len))
        strings.append('    } gl;')     # struct
        strings.append('};')            # union GL3WProcs
        h_template = h_template.replace(strings[0], '\n'.join(strings))

        strings = ['/* OpenGL functions */']
        for proc in procs:
            strings.append('#define {0: <{2}} imgl3wProcs.gl.{1}'.format(proc, proc[2:], max_proc_len))
        h_template = h_template.replace(strings[0], '\n'.join(strings))

        # Embed GL/glcorearb.h
        h_template = h_template.replace('#include <GL/glcorearb.h>', glcorearb)

        # Remove KHR/khrplatform.h include, we use our own minimal typedefs from it
        h_template = h_template.replace('#include <KHR/khrplatform.h>', '')

        # Embed gl3w.c
        strings = ['static const char *proc_names[] = {']
        for proc in procs:
            strings.append('    "{0}",'.format(proc))
        h_template = h_template.replace(strings[0], '\n'.join(strings))

        fp.write(h_template)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
