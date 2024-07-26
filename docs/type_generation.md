# Generating ZERP types locally on your system

A utility script is provided which allows you to generate ZERP types locally on your system. These types can be used by LSP's to provide auto-completion in your editor and by static type checking tools like MyPy to validate your code.

## Setup

The only requirement for executing this script is to have a valid WAMP connection defined in your `~/izaber.yaml` file or exposed as an environment variable.

## Quick Start

After installing the library and configuring your WAMP connection, execute the following command in your terminal:

```bash
python3 -m izaber_wamp_zerp generate-types
```

The type generation was successful if you see output similar to the following in your console.

```bash
Generating models: 100%|██████████| 865/865

865/865 models successfully generated.
- 133/865 stale models ignored.
- 0/865 models failed to generate.

```

After successful installation, interacting with the `zerp` object should provide type-hints to your tools. See [Interacting with ZERP](./usage_in_scripts.md) for more information.



In order to suppress and continue past model generation errors, use the `--ignore-errors` flag:

```bash
python3 -m izaber_wamp_zerp generate-types --ignore-errors
```