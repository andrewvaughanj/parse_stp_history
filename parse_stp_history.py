#!/usr/bin/env python3

# The MIT License
#
# Copyright (c) 2020 Andrew V. Jones <andrewvaughanj@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import pygit2
import os
import sys
from datetime import datetime, timezone, timedelta

# Make sure I don't make any typos
VIJAY_NAME = "Vijay Ganesh"


def transform_name(name):
    """
    Helper function to convert a commit that looks like Vijay into something that tracks Davild Dill too
    """

    # Vijay's email changes, but his name always has "ganesh" in it
    if "Ganesh".lower() in name.lower():
        contributor = set([VIJAY_NAME, "David L. Dill"])
    else:
        contributor = set([name.title()])
    return contributor


def get_git_type(action):
    """
    Helper to convert a git action into a string
    """
    return {
        pygit2.GIT_DELTA_ADDED: "GIT_DELTA_ADDED",
        pygit2.GIT_DELTA_CONFLICTED: "GIT_DELTA_CONFLICTED",
        pygit2.GIT_DELTA_COPIED: "GIT_DELTA_COPIED",
        pygit2.GIT_DELTA_DELETED: "GIT_DELTA_DELETED",
        pygit2.GIT_DELTA_IGNORED: "GIT_DELTA_IGNORED",
        pygit2.GIT_DELTA_MODIFIED: "GIT_DELTA_MODIFIED",
        pygit2.GIT_DELTA_RENAMED: "GIT_DELTA_RENAMED",
        pygit2.GIT_DELTA_TYPECHANGE: "GIT_DELTA_TYPECHANGE",
        pygit2.GIT_DELTA_UNMODIFIED: "GIT_DELTA_UNMODIFIED",
        pygit2.GIT_DELTA_UNREADABLE: "GIT_DELTA_UNREADABLE",
        pygit2.GIT_DELTA_UNTRACKED: "GIT_DELTA_UNTRACKED",
    }[action]


def calculate_stats(path_to_repo):
    """
    Walks the repo history and tries to calculate ownership
    """

    # Open-up a handle to the repo
    repo = pygit2.Repository(path_to_repo)

    # Flags for getting the history in reverse order
    history_flags = pygit2.GIT_SORT_TIME | pygit2.GIT_SORT_REVERSE

    # A mapping from files to the people who 'own' that file
    owners = {}

    # A mapping from files to the date they were 'created'
    created_on = {}

    # The set of all contributors
    all_contributors = set()

    # The last time Vijay committed to the STP repo
    last_vijay_date = None

    # Are processing the first commit or not?
    first = True

    # A magic git hash that exists in every, empty repo
    last = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

    # We now walk all commits
    for commit in repo.walk(repo.head.peel().oid.hex, history_flags):

        # Get the difference between this commit and the previous one
        diff = repo.diff(last, commit.hex)

        # Previous commit is now the current
        last = commit.hex

        # As Git to try to calculate file moves
        diff.find_similar()

        # For each change in this commit
        for delta in diff.deltas:

            if first or delta.status in [
                pygit2.GIT_DELTA_ADDED,
                pygit2.GIT_DELTA_MODIFIED,
            ]:
                # If we're adding or changing a file ...

                # File paths shouldn't have changed
                assert delta.old_file.path == delta.new_file.path

                # If we're processing the first commit
                if first:

                    # Everything is added
                    assert delta.status == pygit2.GIT_DELTA_ADDED

                    # Mark this is a Vijay commit
                    contributor = transform_name(VIJAY_NAME)
                else:

                    # Ensure we correctly work out who the owner is
                    contributor = transform_name(commit.author.name)

                # Find the date/time of this commit
                tzinfo = timezone(timedelta(minutes=commit.author.offset))
                commit_time = datetime.fromtimestamp(float(commit.author.time), tzinfo)

                # If this is a Vijay commit, store the last date
                if VIJAY_NAME in contributor:
                    last_vijay_date = commit_time

                if delta.status == pygit2.GIT_DELTA_ADDED:
                    # If we're adding a file, then we expect it not to exist
                    assert delta.new_file.path not in owners

                    # So we directly set the contributor
                    owners[delta.new_file.path] = contributor

                    # Store when this file was created
                    created_on[delta.new_file.path] = commit_time
                else:
                    # If we're modifying a file, then we expect it to exist
                    assert delta.new_file.path in owners

                    # Create the union of the contributors
                    owners[delta.new_file.path] |= contributor

                    # Don't change the date!

                # Record this contributor
                all_contributors |= contributor

            elif delta.status in [pygit2.GIT_DELTA_RENAMED, pygit2.GIT_DELTA_DELETED]:
                # Renaming also deletes, so these are merged

                if delta.status == pygit2.GIT_DELTA_RENAMED:
                    # Renaming a file does not give ownership

                    # The new file shouldn't exist
                    assert delta.new_file.path not in owners

                    # Copy the ownership to the new file
                    owners[delta.new_file.path] = owners[delta.old_file.path]

                    # Store when this file was created
                    created_on[delta.new_file.path] = created_on[delta.old_file.path]

                # Delete the old ownership
                del owners[delta.old_file.path]

                # Delete the old time
                del created_on[delta.old_file.path]

            else:
                # Need to make sure we've handled everything
                raise RuntimeError(
                    "You haven't handled: {:s}".format(get_git_type(delta.status))
                )

        # If we're here, we've handled the first commit
        first = False

    print(
        "{vijay:s} last commited on {date:s}".format(
            vijay=VIJAY_NAME, date=last_vijay_date.strftime("%c %z")
        )
    )

    # Walk all the files
    for fname, owners in owners.items():

        # Ensure we haven't done anything silly, and this file should definitely exist!
        assert os.path.exists(os.path.join(path_to_repo, fname))

        # Get the set for Vijay + David
        vijay_set = transform_name(VIJAY_NAME)

        # Find when this file was added
        added_date = created_on[fname]

        # Was it added *before* Vijay's last date
        before_last_date = added_date < last_vijay_date

        if owners == vijay_set:
            # Is this file exclusively owned by Vijay/David?
            ownership = "Complete"
        elif vijay_set & owners:
            # If this file partially owned by Vijay/David?
            ownership = "Partial"
        elif before_last_date:
            # Did this file exist before Vijay's last commit?
            ownership = "Inherited"
        else:
            # Did it come afterwards?
            ownership = "None"

        formatted_date = added_date.strftime("%c %z")
        print(
            "{ownership:s} -- {name:s} (first added: {date:s})".format(
                ownership=ownership, name=fname, date=formatted_date
            )
        )


def main():
    # Name of the repo we want to process
    path_to_repo = "/home/avj/clones/stp/master"

    # Caulate the stats
    calculate_stats(path_to_repo)

    # We're done!
    return 0


if __name__ == "__main__":
    sys.exit(main())

# EOF
