# Importamos el administrador y mensajes de Django.
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

# Importamos nuestros modelos.
from .models import (
    Categoria,
    Producto,
    Pedido,
    DetallePedido,
)


# =========================================================
# ADMINISTRACIÓN DE CATEGORÍAS
# =========================================================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "activo",
    )
    search_fields = (
        "nombre",
    )
    list_filter = (
        "activo",
    )


# =========================================================
# ADMINISTRACIÓN DE PRODUCTOS
# =========================================================

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "categoria",
        "precio",
        "stock",
        "activo",
    )
    list_editable = (
        "precio",
        "stock",
        "activo",
    )
    search_fields = (
        "nombre",
        "descripcion",
    )
    list_filter = (
        "categoria",
        "activo",
    )
    ordering = (
        "nombre",
    )


# =========================================================
# DETALLE DEL PEDIDO DENTRO DEL PEDIDO
# =========================================================

class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    fields = (
        "producto",
        "cantidad",
        "precio_unitario",
    )


# =========================================================
# ADMINISTRACIÓN DE PEDIDOS
# =========================================================

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "fecha",
        "total",
        "estado",
        "stock_devuelto",
    )
    readonly_fields = (
        "total",
        "stock_devuelto",
    )
    search_fields = (
        "usuario__username",
    )
    list_filter = (
        "estado",
        "fecha",
    )
    inlines = [
        DetallePedidoInline,
    ]

    # Validar transiciones de estado desde /admin
    def save_model(self, request, obj, form, change):
        if change:
            pedido_anterior = Pedido.objects.get(pk=obj.pk)
            if pedido_anterior.estado != obj.estado:
                try:
                    nuevo_estado = obj.estado
                    obj.estado = pedido_anterior.estado
                    obj.cambiar_estado(nuevo_estado)
                    return
                except ValidationError as e:
                    messages.error(request, e.message)
                    return
        super().save_model(request, obj, form, change)

    # Actualizar stock y total cuando se modifican cantidades en /admin
    def save_formset(self, request, form, formset, change):
        instancias = formset.save(commit=False)
        for detalle in instancias:
            if detalle.pk:
                detalle_anterior = DetallePedido.objects.get(pk=detalle.pk)
                if detalle_anterior.cantidad != detalle.cantidad:
                    try:
                        nueva_cantidad = detalle.cantidad
                        detalle.cantidad = detalle_anterior.cantidad
                        detalle.actualizar_cantidad(nueva_cantidad)
                        continue
                    except ValidationError as e:
                        messages.error(request, e.message)
                        continue
            detalle.save()
        formset.save_m2m()
        form.instance.recalcular_total()
# =========================================================
# ADMINISTRACIÓN DE DETALLES
# =========================================================

@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = (
        "pedido",
        "producto",
        "cantidad",
        "precio_unitario",
    )
    search_fields = (
        "producto__nombre",
        "pedido__usuario__username",
    )