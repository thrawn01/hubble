package hubble

import (
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"os/user"
	"path"
	"path/filepath"
	"strings"
	"unicode"

	"github.com/pkg/errors"
	"github.com/zieckey/goini"
)

func Run(argv []string, rcLocations []string) {

	// Read all the rc files
	rc, err := parseRCFiles(rcLocations)
	checkErr(err, "while parsing configs")

	// Figure out which env the user has chosen
	conf, cmdArgs, choice, err := evalArgs(argv, rc)
	checkErr(err, "")

	if conf.Debug {
		fmt.Printf("Config:\n")
		fmt.Printf("   Env: %s\n", choice)
		fmt.Printf("   IncludeLocalEnv: %t\n", conf.IncludeLocalEnv)
	}

	// Run the command in each environment
	environments := getEnvironments(choice, rc)
	var cmds []*exec.Cmd

	// Execute a command for each environment defined
	for _, env := range environments {
		// Get the command to execute
		cmd, err := getCmd(argv, rc, env)
		checkErr(err, "")

		if conf.Debug {
			fmt.Printf("===========================\n")
			fmt.Printf("Cmd: \n    %s\n", cmd)
			fmt.Printf("Environment:\n")
			fmt.Printf("    %s\n", strings.Join(env.ToSlice(), "\n    "))
		}

		// Include our current environment
		if conf.IncludeLocalEnv {
			for _, pair := range os.Environ() {
				parts := strings.SplitN(pair, "=", 2)
				if _, ok := env[parts[0]]; !ok {
					env[parts[0]] = parts[1]
				}
			}
		}

		cmds = append(cmds, &exec.Cmd{
			Path:   cmd,
			Args:   append([]string{cmd}, cmdArgs...),
			Stdout: os.Stdout,
			Stderr: os.Stderr,
			Env:    env.ToSlice(),
		})
	}

	// If only one command, then return the appropriate return code
	if len(cmds) == 1 {
		err := cmds[0].Run()
		if err != nil {
			e, ok := err.(*exec.ExitError)
			if !ok {
				checkErr(err, "")
			}
			os.Exit(e.ProcessState.ExitCode())
		}
		return
	}

	var hadErr bool
	for _, cmd := range cmds {
		if err := cmd.Run(); err != nil {
			fmt.Print(err)
			hadErr = true
		}
	}

	if hadErr {
		os.Exit(1)
	}
}

func expand(path string) string {
	usr, _ := user.Current()
	dir := usr.HomeDir
	if path == "~" {
		// In case of "~", which won't be caught by the "else if"
		path = dir
	} else if strings.HasPrefix(path, "~/") {
		// Use strings.HasPrefix so we don't match paths like
		// "/something/~/something/"
		path = filepath.Join(dir, path[2:])
	}
	return path
}

// Finds all given and default configs loading each in order
func parseRCFiles(p []string) (*goini.INI, error) {
	paths := []string{expand("~/.hubblerc"), ".hubblerc"}
	paths = append(paths, p...)

	result := goini.New()
	for _, file := range paths {
		contents, err := ioutil.ReadFile(file)
		if err != nil {
			continue
		}
		ini := goini.New()
		ini.SetParseSection(true)
		ini.SetSkipCommits(true)
		if err := ini.Parse(contents, goini.DefaultLineSeparator, goini.DefaultKeyValueSeparator); err != nil {
			return nil, errors.Wrapf(err, "while parsing '%s'", file)
		}
		result.Merge(ini, true)
	}

	if len(result.GetAll()) == 0 {
		return nil, fmt.Errorf("no configs read; attempted [%s]", strings.Join(paths, ", "))
	}

	return result, nil
}

func checkErr(err error, msg string) {
	if err != nil {
		if msg != "" {
			fmt.Fprintf(os.Stderr, "-- %s: %s\n", msg, err)
		} else {
			fmt.Fprintf(os.Stderr, "-- %s\n", err)
		}
		os.Exit(1)
	}
}

func getCmd(argv []string, conf *goini.INI, env envMap) (string, error) {
	// If our invocation name is not 'hubble'
	if !strings.HasSuffix(argv[0], "hubble") {
		baseName := path.Base(argv[0])
		if result, ok := conf.SectionGet("hubble-commands", baseName); ok {
			return result, nil
		}
	}

	// TODO: If hubbleArgs has an execute option defined

	// Else, use the cmd if defined
	cmd, ok := env["cmd"]
	if !ok {
		return "", errors.New("please specify a 'cmd' somewhere in your config")
	}
	return exec.LookPath(cmd)
}

type envMap map[string]string

func (e envMap) ToSlice() []string {
	result := make([]string, len(e))
	var i = 0
	for k, v := range e {
		result[i] = fmt.Sprintf("%s=%s", k, v)
		i++
	}
	return result
}

func getEnvironments(choice string, conf *goini.INI) []envMap {
	root := make(map[string]string)
	sections := []string{choice}

	// Source values that are not in a section
	kv, ok := conf.GetKvmap(goini.DefaultSection)
	if ok {
		root = copyEnv(kv)
	}

	// Support the original hubble default section
	kv, ok = conf.GetKvmap("hubble")
	if ok {
		for k, v := range kv {
			root[k] = v
		}
	}

	// Populate the environment variables from the chosen section
	kv, _ = conf.GetKvmap(choice)
	for k, v := range kv {
		if k == "meta" {
			sections = toSlice(v, nil)
		}
		root[k] = v
	}

	var result []envMap
	for _, section := range sections {
		// Copy the values from the inherited env
		env := copyEnv(root)
		// Add the name of the section
		env["section"] = section
		// Add the chosen section
		kv, _ := conf.GetKvmap(choice)
		for k, v := range kv {
			env[k] = v
		}
		// TODO: Expand opt.%s
		// TODO: Expand ${variables}
		// TODO: run opt-cmd and opt-env
		result = append(result, env)
	}
	return result
}

func copyEnv(src map[string]string) map[string]string {
	dst := make(map[string]string, len(src))
	for k, v := range src {
		dst[k] = v
	}
	return dst
}

type Config struct {
	IncludeLocalEnv bool
	Debug           bool
}

func evalArgs(argv []string, rc *goini.INI) (conf *Config, cmdArgs []string, env string, err error) {
	// TODO: Get this from thrawn01/cli
	conf = &Config{IncludeLocalEnv: true}
	env, ok := rc.Get("default-env")
	if !ok {
		// If no default-env defined, env should be the first arg
		if len(argv) == 1 {
			return nil, nil, "", errors.New("no 'default-env' defined and no environment provided vi cli args")
		}
		env = argv[1]
		if len(argv) > 2 {
			cmdArgs = argv[2:]
		}
	}

	_, ok = rc.GetKvmap(env)
	if !ok {
		var sections []string
		for k := range rc.GetAll() {
			if k == goini.DefaultSection {
				continue
			}
			sections = append(sections, k)
		}
		return nil, nil, "", fmt.Errorf("env '%s' not defined in config; environments configured: %s",
			env, strings.Join(sections, ","))
	}
	// TODO: Use thrawn/cli to parse what args we know about, and leave the rest for the command

	// TODO: change this to a cli arg
	if os.Getenv("HUBBLE_DEBUG") != "" {
		conf.Debug = true
	}

	return conf, cmdArgs, env, nil
}

// Given a python like array, return a slice of string items.
// Return the entire string as the first item if no comma is found.
// Ignores commas inside a quote `["1,234", "20,2020", "1,1"]`
func toSlice(value string, modifiers ...func(s string) string) []string {
	value = strings.Trim(value, "[]")
	lastQuote := rune(0)
	result := strings.FieldsFunc(value, func(c rune) bool {
		switch {
		case c == lastQuote:
			lastQuote = rune(0)
			return false
		case lastQuote != rune(0):
			return false
		case unicode.In(c, unicode.Quotation_Mark):
			lastQuote = c
			return false
		default:
			return c == ','
		}
	})
	// Apply the modifiers
	for _, modifier := range modifiers {
		for idx, item := range result {
			result[idx] = modifier(item)
		}
	}
	return result
}
