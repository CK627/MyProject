# ctfsweep 补全（bash）：source 本文件，或放入 /etc/bash_completion.d/。
_ctfsweep() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="-k --keywords --min-score --no-decode --depth --limit --extract --extract-dir --pwd-file --config --version -h --help"
    case "$prev" in
        -k|--keywords)
            COMPREPLY=( $(compgen -W "flag ctf key secret" -- "$cur") )
            return 0
            ;;
        --extract-dir)
            COMPREPLY=( $(compgen -d -- "$cur") )
            return 0
            ;;
        --pwd-file|--config)
            COMPREPLY=( $(compgen -f -- "$cur") )
            return 0
            ;;
    esac
    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
    else
        COMPREPLY=( $(compgen -f -- "$cur") )
    fi
}
complete -o filenames -F _ctfsweep ctfsweep
