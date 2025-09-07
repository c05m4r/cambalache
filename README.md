# Cambalache JSON Modifier

Command-line tool that generates multiple JSON objects from a JSON template and a wordlist. It allows modifying specific fields within json_data, either by replacing their values, adding the words as prefixes and/or suffixes, or generating sequential values.

## Environment Setup

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc
```

### Install dependencies

```bash
uv sync
```

## Basic Usage

```bash
uv run cambalache.py [OPTIONS] template.json wordlist.txt output.json
```

  * `template.json`: Your base JSON file (the first object is used).
  * `wordlist.txt`: File with one word per line (ignored in generator mode).
  * `output.json`: Name of the resulting JSON file.

-----

## Examples

For the examples, we will use these input files:

**`template.json`:**

```json
[
  {
    "testid": "tc101",
    "description": "testcase",
    "json_data": {
      "email": "example@gmail.com",
      "username": "testuser",
      "city": "Lucinico"
    }
  }
]
```

**`wordlist.txt`:**

```
user1
admin
test_ palabra
```

-----

### Replace Mode (Default - Overwrites values)

**1. Replace ALL fields within `json_data`**
(Default: if you don't specify `--include` or `--ignore`)

```bash
uv run cambalache.py template.json wordlist.txt output.json
```

*Result: 3 objects. In the first one, `email`, `username`, and `city` will be "user1". In the second, they will be "admin", etc.*

**2. Replace ONLY the `email` field**

```bash
uv run cambalache.py template.json wordlist.txt output.json --include email
```

*Result: 3 objects. `email` will be "user1", "admin", "test\_ palabra". `username` and `city` remain original.*

**3. Replace ALL EXCEPT the `city` field**

```bash
uv run cambalache.py template.json wordlist.txt soutput.json --ignore city
```

*Result: 3 objects. `email` and `username` will be replaced by "user1", "admin", etc. `city` remains original ("Lucinico").*

-----

### Generation Mode (Creates NEW objects with prefixes/suffixes)

**4. Generate by adding as a PREFIX to ALL fields**

```bash
uv run cambalache.py template.json wordlist.txt output.json --prefix
```

*Result: 9 objects (3 words x 3 fields). You will have objects where `email` is "[dirección de correo electrónico eliminada]", others where `username` is "user1testuser", others where `city` is "user1Lucinico", and so on for "admin" and "test\_ palabra".*

**5. Generate by adding as a SUFFIX to ALL fields**

```bash
uv run cambalache.py template.json wordlist.txt output.json --suffix
```

*Result: 9 objects. You will have `email` as "example@gmail.comuser1", `username` as "testuseruser1", `city` as "Lucinicouser1", etc.*

**6. Generate objects with PREFIX and SUFFIX (separate) for ALL fields**

```bash
uv run cambalache.py template.json wordlist.txt output.json --both
```

*Result: 18 objects (3 words x 3 fields x 2 [prefix and suffix]). For each word/field combination, it generates one object with a prefix and another with a suffix. E.g., one with `email`="[dirección de correo electrónico eliminada]" and another with `email`="example@gmail.comuser1".*

-----

### Combining Modes and Field Selection

**7. Generate with PREFIX, but ONLY for the `username` field**

```bash
uv run cambalache.py template.json wordlist.txt output.json --prefix --include username
```

*Result: 3 objects. Only the `username` field is modified (e.g., "user1testuser"), the others remain as in the template.*

**8. Generate with SUFFIX, ignoring `email` and `city` (i.e., ONLY `username`)**

```bash
uv run cambalache.py template.json wordlist.txt output.json --suffix --ignore email city
```

*Result: 3 objects. Only `username` is modified with a suffix (e.g., "testuseruser1").*

**9. Generate with PREFIX and SUFFIX (separate), ONLY for `email` and `city`**

```bash
uv run cambalache.py template.json wordlist.txt output.json --both --include email city
```

*Result: 12 objects (3 words x 2 fields x 2 [prefix/suffix]). Objects modified only in `email` or `city`, with both prefix and suffix versions.*

-----

### Generator Mode (Creates sequential values)

**10. Generate sequential values for a specific field**

```bash
uv run cambalache.py template.json dummy.txt output.json --gen username
```

*Result: 10 objects (by default). The `username` field will have sequential values like "testuser1", "testuser2", "testuser3", etc., based on the original value in the template. Other fields remain unchanged.*

**Example with a user template:**

If your template has:
```json
{
  "json_data": {
    "identificador": "usuario_example",
    "email": "usuario_example@siu.edu.ar",
    "password": "abc123456"
  }
}
```

Running:
```bash
uv run cambalache.py usuarios.json dummy.txt usuarios_generados.json --gen identificador
```

Will generate objects with:
- `identificador`: "usuario_example1", "usuario_example2", "usuario_example3", ...
- `email` and `password` remain as in the original template

**Note:** In generator mode (`--gen`), the wordlist file is required but ignored. You can use any dummy file as the second argument.

-----

## Available Options

```bash
uv run cambalache.py --help
```

### Arguments:
- `TEMPLATE_PATH`: Path to the JSON template file (required)
- `WORDLIST_PATH`: Path to the wordlist file (required, but ignored in `--gen` mode)
- `OUTPUT_PATH`: Path to the output JSON file (required)

### Options:
- `--include -i`: Specify which fields in json_data to modify exclusively
- `--ignore -x`: Specify which fields in json_data to ignore
- `--prefix`: Generation mode - add words as prefix to original values
- `--suffix`: Generation mode - add words as suffix to original values
- `--both`: Generation mode - create objects with both prefix AND suffix (separate objects)
- `--gen`: Generator mode - create sequential values for the specified field (e.g., user1, user2, user3...)

**Note:** The modes `--prefix`, `--suffix`, `--both`, and `--gen` are mutually exclusive.
