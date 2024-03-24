VALID_TARGETS=(openssl community followup resolve)
TARGET=unknown

VALID_RESOLUTIONS=(fixed wontfix duplicate notabug)
RESOLUTION=none

RESOLUTION_ID=0

VALID_RELEASES=()
RELEASE=none

VALID_PRIORITIES=(Immediate High Medium Low)
PRIORITY=low

IS_URGENT=no
IS_IMPORTANT=unknown
IS_REGRESSION=unknown

VALID_TYPES=(bug feature documentation cleanup performance refactor question)
TYPE=none


GH_PROJECT_ID=none
GH_PROPOSED_RELEASE_FIELD=none
GH_PRIORITY_FIELD=none
GH_RELEASE_LIST=()

function load_github_ids {
    local i
    git config --local --get-regexp triage > /dev/null 2>&1
    if [ $? -eq 0 ]
    then
        # we have our cached values, load them
        GH_PROJECT_ID=$(git config --local --get triage.gh-project-id)
        GH_PROPOSED_RELEASE_FIELD=$(git config --local --get triage.gh-proposed-release-field)
        GH_PRIORITY_FIELD=$(git config --local --get triage.gh-priority-field)
        for i in $(git config --local --get triage.gh-release-list)
        do
            GH_RELEASE_LIST+=($i)
        done
    else
        # We need to fetch and cache them
        GH_PROJECT_ID=$(gh project list --owner openssl --format json --jq '.projects[] | select (.title == "Project Board") | .id')
        git config --local triage.gh-project-id $GH_PROJECT_ID
        GH_PROPOSED_RELEASE_FIELD=$(gh project field-list --owner openssl 2 --format json --jq '.fields[] | select(.name == "Proposed Release") | .id')
        git config --local triage.gh-proposed-release-field $GH_PROPOSED_RELEASE_FIELD
        GH_PRIORITY_FIELD=$(gh project field-list --owner openssl 2 --format json --jq '.fields[] | select(.name == "Priority") | .id')
        git config --local triage.gh-priority-field $GH_PRIORITY_FIELD
        CONFIG_LIST=""
        for i in $(gh project field-list --owner openssl 2 --format json --jq '.fields[] | select(.name == "Proposed Release") | .options[] | .name')
        do
            GH_RELEASE_LIST+=($i)
            CONFIG_LIST="$CONFIG_LIST $i"
        done
        git config --local triage.gh-release-list "$CONFIG_LIST" 
    fi
}

needed_tools=(jq gh git)
function check_tools {
    local tool_pass=yes
    for i in $(echo ${needed_tools[@]})
    do
        which $i > /dev/null 2>&1
        if [ $? -ne 0 ]
        then
            echo "This tool requires $i to be installed"
            tool_pass=no
        fi
    done

    if [ "$tool_pass" == "no" ]
    then
        exit 1
    fi
}

function check_gh_auth {
    gh auth status > /dev/null 2>&1
    if [ $? -ne 0 ]
    then
        echo "You are not logged into the github cli, attempting login"
        if [ ! -f ~/.ghtoken ]
        then
            echo "You don't have an auth token in ~/.ghtoken"
            echo "Create one by going to https://github.com/settings/tokens"
            echo "And placing the generated token in ~/.ghtoken"
            exit 1
        fi
        gh auth login --with-token < ~/.ghtoken
    fi
}

function check_repo {
    local selection
    git config --get-regex remote | grep -q "gh-resolved"
    if [ $? -ne 0 ]
    then
        echo "Please select one of the following repositories to triage:"
        # Only display push repo urls, trimming leading protocol/host section of url
        # and trailing .git.  thats what gh expects
        git remote -v | awk '/(push)/ {print $2}' | sed -e"s/.*github.com[\:\/]*//" -e"s/\.git//"
        echo "Please enter one of the above strings: "
        read selection
        gh repo set-default $selection > /dev/null 2>&1
        if [ $? -ne 0 ]
        then
            echo "Failed to set default repository"
            exit 1
        fi
    fi

}

# Prints a list of issues that don't have a triage label applied
function list_untriaged_issues {
    gh issue list --search '-label:"triaged: bug","triaged: feature","triaged: performance","triaged: refactor","triaged: question","triaged: documentation","triaged: cleanup","triaged: design"'
}

function tool_startup {
    check_tools
    check_gh_auth
    check_repo
}
