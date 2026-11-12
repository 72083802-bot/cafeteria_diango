# =========================================================
# FORMULARIOS DEL SISTEMA
# =========================================================

# Sistema de formularios de Django.
from django import forms

# Modelos que utilizaremos dentro de los formularios.
from .models import Categoria, Pedido



# =========================================================
# FORMULARIO PARA BUSCAR PRODUCTOS
# =========================================================

class ProductoFiltroForm(forms.Form):

    # -----------------------------------------------------
    # BÚSQUEDA POR NOMBRE
    # -----------------------------------------------------

    # Campo de texto opcional.
    busqueda = forms.CharField(
        required=False,
        label="Buscar producto",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ejemplo: café",
            }
        ),
    )


    # -----------------------------------------------------
    # FILTRO POR CATEGORÍA
    # -----------------------------------------------------

    # ModelChoiceField permite llenar automáticamente
    # el selector utilizando objetos de Categoria.
    categoria = forms.ModelChoiceField(
        required=False,

        # Solo mostramos categorías activas.
        queryset=Categoria.objects.filter(
            activo=True
        ).order_by("nombre"),

        # Opción utilizada cuando no queremos
        # filtrar por una categoría específica.
        empty_label="Todas las categorías",

        label="Categoría",

        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )


    # =====================================================
    # VALIDACIÓN DEL FORMULARIO
    # =====================================================

    def clean(self):

        # Ejecutamos primero las validaciones
        # proporcionadas por Django.
        datos = super().clean()

        fecha_desde = datos.get("fecha_desde")

        fecha_hasta = datos.get("fecha_hasta")

        # Comprobamos que la fecha inicial
        # no sea posterior a la fecha final.
        if (
            fecha_desde
            and fecha_hasta
            and fecha_desde > fecha_hasta
        ):

            raise forms.ValidationError(
                "La fecha inicial no puede ser "
                "posterior a la fecha final."
            )

        return datos
