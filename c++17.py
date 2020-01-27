# -*- python -*-
#######################################################################################################################
#
# Tool: c++17
#
# Description: sets compiler flags for C++17 compatibility
#
# Command-line options:
#   <none>
#
#######################################################################################################################

def exists(env):
    return True

def generate(env):
    # MSVC
    env.AppendUnique(CXXFLAGS = ['/std:c++17'])
