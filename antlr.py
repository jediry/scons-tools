import os
import re

# TODO:
#   figure out how to make grammar files depend on supergrammar .txt files
#   figure out how to make cpp files depend on lexer/parser headers
_parserRE      = re.compile(r'class\s+(\S+)\s+extends\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*(\(.*\))?\s*;', re.MULTILINE)
_exportVocabRE = re.compile(r'exportVocab\s*=\s*(\S+);',            re.MULTILINE)
_classPrefixRE = re.compile(r'^(\S+?)(Lexer|Parser|TreeParser)')

# Mapping of filename to list of parser descriptors
_parsersForFile = {}

# Reverse mapping of parser class names to filenames
_fileForParser = {}


def _IsAntlrTempFile(node):
    (path, sep, basename) = str(node).rpartition('/')
    return basename.startswith('expanded')


def _ParseAntlrFile(node):
    # Mappings of various parser types to their info. Each item is a Dictioanry
    # with the following keys:
    #       class: the name of the parser/lexer class
    #       superclass: the name of the parser/lexer superclass
    #       vocab: the name of the export vocabulary
    parsers = []

    # Scan each line of the file for important patterns, identifying parsers,
    # lexers, tree parsers, and exported vocabularies
    contents = node.get_text_contents().splitlines()

    for line in contents:

        # Is it a Parser?
        match = _parserRE.search(line)
        if match != None:
#            print("Parser: " + match.group(1))
            parsers.append({
                'class':      match.group(1),
                'superclass': match.group(2),
                'vocab':      match.group(1),
            })
            continue

        # OK, how about an exportVocab statement?
        match = _exportVocabRE.search(line)
        if match != None:
#            print("Export: " + match.group(1))
            if len(parsers) != 0:
                parsers[-1]['vocab'] = match.group(1)
            else:
                print("Hmmm...exportVocab occurred outside of a parser/lexer!")
            continue

    # Store the mapping and reverse mapping
    fn = str(node)
    _parsersForFile[fn] = parsers
#     print("Finished reading Antlr file " + fn)
#     print("Build-target path is ")
#     node.alter_targets()
    for p in parsers:
        _fileForParser[p['class']] = node


def _GetParsersForFile(node):
    file = str(node)
    if not file in _parsersForFile:
        _ParseAntlrFile(node)
    return _parsersForFile[file]


def _GetFileForParser(klass, env):
    # See if we've already found this parser
    if klass in _fileForParser:
#         print("Already had parser " + klass + " from file " + str(_fileForParser[klass]))
        return _fileForParser[klass]

    # Crap. Don't have it. We'll have to search. We'll start by hunting down
    # all of the .g files in 'path'. We'll parse every one of them if we
    # have to.

    # But if the author was sensible, we shouldn't have to, as something like
    # SnorkleParser will be defined in Snorkle.g, and we should only have to
    # actually read one .g file. If the author was dumb, we may have to read
    # them all. Let's see if 'klass' is something like SnorkleParser or
    # SnorkleLexer, or SnorkleTreeParser.
    prefixMatch = _classPrefixRE.match(klass)
    if prefixMatch != None:
        bestMatchPrefix = prefixMatch.group(1)
    else:
        bestMatchPrefix = None

    # Run through all of our grammar include paths, looking for our 'best' match,
    # if we can find it, and accumulating other .g files as we find them.
    paths = ['/home/jediry/Documents/Development/Media/terrainosaurus/src/terrainosaurus/io']
    grammarFiles = []
    for path in paths:
        files = env.Glob(path + '/*.g')
        for f in files:
            (path, sep, basename) = str(f).rpartition('/')

            # If the filename starts with our 'best' prefix and hasn't been read
            # yet, consider it our best match, and stick it at the head of the list.
            # (If it *has* already been read, then it clearly isn't our best match,
            # or else we'd have taken the trivial return at the start of this function.)
            if bestMatchPrefix != None \
            and basename.startswith(bestMatchPrefix) \
            and f not in _parsersForFile:
#                 print("Probable best match for " + klass + " is " + str(f))
                grammarFiles.insert(0, f)
            elif _IsAntlrTempFile(f):
                # This is an intermediate "flattened" grammar. Ignore it.
                pass
            else:
                grammarFiles.append(f)

    # Run through all the files we collected. Any 'best' match will be at the
    # front of this list, and so will be read first.
    for f in grammarFiles:
        if f not in _parsersForFile:    # i.e., this file has not been read yet
            _ParseAntlrFile(f)
        if klass in _fileForParser:     # i.e., class 'klass' has been located
#             print("Found class " + klass + " in file " + str(f))
            return _fileForParser[klass]

    print("Failed to locate .g file for " + klass)
    return None


def _GetAntlrFileDependencies(node, env):
    # Get the set of parsers defined in 'node'
    parsers = _GetParsersForFile(node)

    # Look up all their superclasses, and find the files those are in
    fileSet = set()
    for p in parsers:
        if p['superclass'] not in ('Lexer', 'Parser', 'TreeParser'):
#             print p['class'] + " has superclass " + p['superclass']
            file = _GetFileForParser(p['superclass'], env)
            if file != None:
                fileSet.add(file)

    # Return the list of results
    files = []
    for f in fileSet:
        files.append(f)
#        print("File " + str(node) + " depends on " + str(f))
    return files


def AntlrFileEmitter(target, source, env):
    # Collect all of the parsers defined in the source file(s)
    parsers = []
    for src in source:
        # Figure out where the targets should go...
        src.duplicate = 1
        parsers += _GetParsersForFile(src)

    # Generate the output filenames. We use a set because multiple parsers
    # might share the same export vocabulary
    targetSet = set()
    for p in parsers:
        targetSet.add(p['class'] + '.hpp')
        targetSet.add(p['class'] + '.cpp')
        targetSet.add(p['vocab'] + 'TokenTypes.hpp')
        targetSet.add(p['vocab'] + 'TokenTypes.txt')

        # If any of the parsers in this file have a superclass, then an
        # intermediate file 'expandedSnorkle.g' will be created.
        if p['superclass'] not in ['Lexer', 'Parser', 'TreeParser']:
            pFile = _GetFileForParser(p['class'], env)
            if pFile != _GetFileForParser(p['superclass'], env):
                (path, sep, basename) = str(pFile).replace('\\', '/').rpartition('/')
                targetSet.add('expanded' + basename)

    # Flatten to a list of filename targets
    target = []
    for t in targetSet:
        target.append(t)
    return (target, source)


def AntlrFileScanner(node, env, path):
    return _GetAntlrFileDependencies(node, env)


def AntlrFileActionGenerator(source, target, env, for_signature):
    commands = []
    for src in source:
        path = src.get_dir()
        dependencies = _GetAntlrFileDependencies(src, env)
        if len(dependencies) > 0:
            depPaths = []
            for dep in dependencies:
                depPaths.append(str(dep))
            includes = ' -glib "%s"' % ';'.join(depPaths)
        else:
            includes = ''
        commands.append('$ANTLR -o "%s" %s "%s"' % (path, includes, src))
    return commands


def generate(env):
    # Scanner for determining grammar file dependencies
    antlrScanner = env.Scanner(
        function = AntlrFileScanner,
        skeys = ['.g']
    )
    env.Append(SCANNERS = antlrScanner)

    # Builder + emitter for antlr files
    from SCons.Builder import Builder
    builder = Builder(generator = AntlrFileActionGenerator,
                      src_suffix = '.g',
                      emitter = AntlrFileEmitter)
    env.Append(BUILDERS = {'AntlrGrammar':builder})

    # Path to the antlr executable
    env.AppendUnique(ANTLR = 'C:\ProgramData\Oracle\java\javapath\java -cp D:/users/jediry/Projects/terrainosaurus/external/antlr-2.7.7/antlr.jar antlr.Tool')
#    env.AppendUnique(ANTLR = 'C:\ProgramData\Oracle\java\javapath\java -cp D:/users/jediry/Projects/terrainosaurus/external/antlr-3.5.2-complete-no-st3.jar org.antlr.Tool')


def exists(env):
   """
   Make sure antlr exists.
   """
   return env.Detect("antlr")
