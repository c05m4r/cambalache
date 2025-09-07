# curl -LsSf https://astral.sh/uv/install.sh | sh
# echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc
# uv sync
# uv run cambalache.py --help

import pandas as pd
import json
import copy
from typing import List, Optional, Dict, Any, Set, Protocol
import typer
import sys
from abc import ABC, abstractmethod
from pathlib import Path


class TransformationStrategy(ABC):
    """Interfaz para las estrategias de transformación de valores."""

    @abstractmethod
    def apply(self, original_value: str, word: str) -> List[Dict[str, str]]:
        """
        Aplica la transformación.
        Retorna una lista de diccionarios, cada uno representando una
        modificación {'field_value': <nuevo_valor>}.
        Para Replace, la clave no importa mucho.
        Para Prefix/Suffix, la clave podría ser útil si quisiéramos info extra.
        Para Both, retornará dos diccionarios.
        """
        pass


class ReplaceStrategy(TransformationStrategy):
    """Estrategia para reemplazar el valor original con la palabra."""

    def apply(self, original_value: str, word: str) -> List[Dict[str, str]]:
        return [{"field_value": word}]


class PrefixStrategy(TransformationStrategy):
    """Estrategia para añadir la palabra como prefijo."""

    def apply(self, original_value: str, word: str) -> List[Dict[str, str]]:
        return [{"field_value": word + original_value}]


class SuffixStrategy(TransformationStrategy):
    """Estrategia para añadir la palabra como sufijo."""

    def apply(self, original_value: str, word: str) -> List[Dict[str, str]]:
        return [{"field_value": original_value + word}]


class BothStrategy(TransformationStrategy):
    """Estrategia para generar tanto prefijo como sufijo en objetos separados."""

    def apply(self, original_value: str, word: str) -> List[Dict[str, str]]:
        return [
            {"field_value": word + original_value},  # Prefijo
            {"field_value": original_value + word},  # Sufijo
        ]


class GeneratorStrategy(TransformationStrategy):
    """Estrategia para generar valores secuenciales basados en un prefijo base."""

    def __init__(self, base_value: str):
        self.base_value = base_value

    def apply(self, original_value: str, word: str) -> List[Dict[str, str]]:
        return [{"field_value": self.base_value + word}]


class AppConfig:
    """Almacena y valida la configuración de la aplicación."""

    def __init__(
        self,
        template_path: Path,
        wordlist_path: Path,
        output_path: Path,
        include_fields: Optional[List[str]],
        ignore_fields: Optional[List[str]],
        prefix: bool,
        suffix: bool,
        both: bool,
        gen_field: Optional[str],
    ):
        self.template_path = template_path
        self.wordlist_path = wordlist_path
        self.output_path = output_path
        self.include_fields = include_fields
        self.ignore_fields = ignore_fields
        self.prefix = prefix
        self.suffix = suffix
        self.both = both
        self.gen_field = gen_field
        self._validate()

    def _validate(self):
        """Realiza validaciones de configuración."""

        active_modes = sum([self.prefix, self.suffix, self.both, bool(self.gen_field)])
        if active_modes > 1:
            typer.echo(
                "Error: Las opciones --prefix, --suffix, --both, y --gen son mutuamente excluyentes.",
                err=True,
            )
            raise typer.Exit(code=1)
        
        if self.gen_field:
            typer.echo(
                "Advertencia: En modo generador (--gen), la wordlist se ignorará.",
                err=True,
            )
            
        if self.include_fields and self.ignore_fields:
            typer.echo(
                "Error: No puedes usar --include y --ignore al mismo tiempo.", err=True
            )
            raise typer.Exit(code=1)

    @property
    def is_generation_mode(self) -> bool:
        """Determina si estamos en modo generación (vs. reemplazo)."""
        return self.prefix or self.suffix or self.both or bool(self.gen_field)

    @property
    def is_generator_mode(self) -> bool:
        """Determina si estamos en modo generador secuencial."""
        return bool(self.gen_field)

    def get_strategy(self, base_value: str = "") -> TransformationStrategy:
        """Selecciona la estrategia de transformación adecuada."""
        if self.gen_field:
            return GeneratorStrategy(base_value)
        elif self.prefix:
            return PrefixStrategy()
        elif self.suffix:
            return SuffixStrategy()
        elif self.both:
            return BothStrategy()
        else:
            return ReplaceStrategy()

    def get_mode_description(self) -> str:
        """Retorna una descripción del modo de operación."""
        if self.gen_field:
            return f"generador secuencial para campo '{self.gen_field}'"
        elif self.prefix:
            return "prefijo"
        elif self.suffix:
            return "sufijo"
        elif self.both:
            return "prefijo Y sufijo (objetos separados)"
        return "Reemplazo"


class DataLoader:
    """Carga los datos desde los archivos de entrada."""

    def load_template(self, path: Path) -> Dict[str, Any]:
        """Carga el primer objeto JSON de la plantilla."""
        try:
            with path.open("r", encoding="utf-8") as f:
                template_list = json.load(f)
            if not isinstance(template_list, list) or not template_list:
                typer.echo(
                    f"Error: El JSON de plantilla '{path}' debe ser una lista con al menos un objeto.",
                    err=True,
                )
                raise typer.Exit(code=1)
            base_obj = template_list[0]
            if "json_data" not in base_obj or not isinstance(
                base_obj.get("json_data"), dict
            ):
                typer.echo(
                    f"Error: El objeto base en '{path}' debe tener una clave 'json_data' que sea un diccionario.",
                    err=True,
                )
                raise typer.Exit(code=1)
            return base_obj
        except json.JSONDecodeError:
            typer.echo(
                f"Error: El archivo de plantilla '{path}' no es un JSON válido.",
                err=True,
            )
            raise typer.Exit(code=1)
        except Exception as e:
            typer.echo(f"Error al leer el archivo de plantilla '{path}': {e}", err=True)
            raise typer.Exit(code=1)

    def load_wordlist(self, path: Path) -> List[str]:
        """Carga la lista de palabras, eliminando duplicados y vacíos."""
        try:
            with path.open("r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines()]
            
            words = []
            seen = set()
            for line in lines:
                if line and line not in seen:
                    words.append(line)
                    seen.add(line)
            
            if not words:
                typer.echo(
                    f"Advertencia: La lista de palabras '{path}' está vacía o no contiene palabras válidas.",
                    err=True,
                )
            return words
        except Exception as e:
            typer.echo(f"Error al leer la lista de palabras '{path}': {e}", err=True)
            raise typer.Exit(code=1)


class JsonWriter:
    """Escribe la lista de objetos JSON a un archivo."""

    def write(self, data: List[Dict[str, Any]], path: Path):
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            typer.echo(
                f"Error al escribir el archivo de salida '{path}': {e}", err=True
            )
            raise typer.Exit(code=1)


class JsonProcessor:
    """Orquesta la carga, procesamiento y generación de datos JSON."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.data_loader = DataLoader()
        self.json_writer = JsonWriter()
        self.base_obj: Dict[str, Any] = {}
        self.words: List[str] = []
        self.target_fields: Set[str] = set()
        self.strategy: Optional[TransformationStrategy] = None

    def _load_inputs(self):
        """Carga la plantilla y opcionalmente la lista de palabras."""
        self.base_obj = self.data_loader.load_template(self.config.template_path)
        
        if not self.config.is_generator_mode:
            self.words = self.data_loader.load_wordlist(self.config.wordlist_path)
        else:
            base_json_data = self.base_obj.get("json_data", {})
            num_objects = max(len(base_json_data), 10)
            self.words = [str(i + 1) for i in range(num_objects)]

    def _determine_target_fields(self):
        """Determina los campos a modificar."""
        base_json_data = self.base_obj.get("json_data", {})
        available_fields = set(base_json_data.keys())

        if self.config.is_generator_mode:
            if self.config.gen_field not in available_fields:
                typer.echo(
                    f"Error: El campo '{self.config.gen_field}' especificado en --gen no existe en json_data.",
                    err=True,
                )
                raise typer.Exit(code=1)
            self.target_fields = {self.config.gen_field}
            base_value = str(base_json_data.get(self.config.gen_field, ""))
            self.strategy = self.config.get_strategy(base_value)
        else:
            if self.config.include_fields:
                self.target_fields = available_fields.intersection(
                    set(self.config.include_fields)
                )
                if len(self.target_fields) != len(self.config.include_fields):
                    missing = set(self.config.include_fields) - available_fields
                    typer.echo(
                        f"Advertencia: Los siguientes campos de --include no existen en json_data: {', '.join(missing)}",
                        err=True,
                    )
                if not self.target_fields:
                    typer.echo(
                        f"Error: Ninguno de los campos especificados en --include ({', '.join(self.config.include_fields)}) existe en json_data.",
                        err=True,
                    )
                    raise typer.Exit(code=1)
            elif self.config.ignore_fields:
                self.target_fields = available_fields - set(self.config.ignore_fields)
                if (
                    not self.target_fields and available_fields
                ):
                    typer.echo(
                        f"Advertencia: Al ignorar {', '.join(self.config.ignore_fields)}, no quedan campos para modificar.",
                        err=True,
                    )
            else:
                self.target_fields = available_fields
            
            self.strategy = self.config.get_strategy()

        if not self.target_fields and available_fields:
            typer.echo(
                "Advertencia: No se han determinado campos objetivo para modificar según las opciones especificadas.",
                err=True,
            )

    def process(self) -> int:
        """Ejecuta el proceso completo de generación."""
        self._load_inputs()
        self._determine_target_fields()

        results: List[Dict[str, Any]] = []
        base_json_data = self.base_obj.get("json_data", {})

        if not self.words:
            typer.echo(
                "Lista de palabras vacía. No se generarán nuevos objetos.", err=True
            )
            self.json_writer.write(results, self.config.output_path)
            return 0
        if not self.target_fields:
            typer.echo(
                "No hay campos objetivo para modificar. No se generarán nuevos objetos.",
                err=True,
            )
            self.json_writer.write(results, self.config.output_path)
            return 0

        typer.echo(f"Modo {self.config.get_mode_description()} activado. Procesando...")

        if self.config.is_generation_mode:
            for word in self.words:
                for field in self.target_fields:
                    original_value = str(base_json_data.get(field, ""))
                    modifications = self.strategy.apply(original_value, word)
                    for mod in modifications:
                        new_obj = copy.deepcopy(self.base_obj)
                        if field in new_obj["json_data"]:
                            new_obj["json_data"][field] = mod["field_value"]
                            results.append(new_obj)
                        else:
                            typer.echo(
                                f"Advertencia interna: Campo '{field}' no encontrado al generar objeto.",
                                err=True,
                            )

        else:
            for word in self.words:
                new_obj = copy.deepcopy(self.base_obj)
                mod = self.strategy.apply("", word)[0]
                value_to_set = mod["field_value"]
                for field in self.target_fields:
                    if field in new_obj["json_data"]:
                        new_obj["json_data"][field] = value_to_set
                    else:
                        typer.echo(
                            f"Advertencia interna: Campo '{field}' no encontrado al reemplazar.",
                            err=True,
                        )
                results.append(new_obj)

        self.json_writer.write(results, self.config.output_path)
        return len(results)


app = typer.Typer(
    help="Herramienta para modificar datos JSON basada en una lista de palabras."
)


@app.command(
    help="Genera objetos JSON modificados basados en una plantilla y una lista de palabras."
)
def main(
    template_path: Path = typer.Argument(
        ...,
        help="Ruta al JSON de plantilla.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    wordlist_path: Path = typer.Argument(
        ...,
        help="Ruta a la lista de palabras.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    output_path: Path = typer.Argument(
        ...,
        help="Ruta al archivo JSON de salida.",
        file_okay=True,
        dir_okay=False,
        writable=True,
        resolve_path=True,
    ),
    include_fields: Optional[List[str]] = typer.Option(
        None,
        "--include",
        "-i",
        help="Lista de campos en json_data a modificar exclusivamente.",
    ),
    ignore_fields: Optional[List[str]] = typer.Option(
        None, "--ignore", "-x", help="Lista de campos en json_data a ignorar."
    ),
    prefix: bool = typer.Option(
        False, "--prefix", help="Modo Generación: palabra como prefijo."
    ),
    suffix: bool = typer.Option(
        False, "--suffix", help="Modo Generación: palabra como sufijo."
    ),
    both: bool = typer.Option(
        False, "--both", help="Modo Generación: crea objetos con prefijo Y sufijo."
    ),
    gen_field: Optional[str] = typer.Option(
        None, "--gen", help="Modo Generador: genera valores secuenciales para el campo especificado."
    ),
):
    """Punto de entrada principal de la aplicación."""
    try:
        config = AppConfig(
            template_path=template_path,
            wordlist_path=wordlist_path,
            output_path=output_path,
            include_fields=include_fields,
            ignore_fields=ignore_fields,
            prefix=prefix,
            suffix=suffix,
            both=both,
            gen_field=gen_field,
        )

        processor = JsonProcessor(config)
        num_results = processor.process()

        typer.echo(
            f"Proceso completado. Se generaron {num_results} objetos en '{config.output_path}'."
        )

    except typer.Exit as e:
        exit_code = getattr(e, 'code', getattr(e, 'exit_code', 1))
        sys.exit(exit_code)
    except Exception as e:
        typer.echo(f"Error inesperado durante la ejecución: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    app()
