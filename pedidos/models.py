# Importamos Decimal para cálculos monetarios exactos.
from decimal import Decimal

# Importamos la configuración general de Django.
from django.conf import settings

# Excepción para validar reglas de negocio.
from django.core.exceptions import ValidationError

# Importamos el sistema de modelos, transacciones y operaciones en BD de Django.
from django.db import models, transaction
from django.db.models import F, Sum


# =========================================================
# MODELO CATEGORIA
# =========================================================

class Categoria(models.Model):

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["nombre"]


# =========================================================
# MODELO PRODUCTO
# =========================================================

class Producto(models.Model):

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos",
    )
    precio = models.DecimalField(
        max_digits=8,
        decimal_places=2,
    )
    stock = models.PositiveIntegerField(default=0)
    imagen = models.ImageField(
        upload_to="productos/",
        blank=True,
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ["nombre"]


# =========================================================
# MODELO PEDIDO
# =========================================================

class Pedido(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PREPARACION = "PREPARACION", "En preparación"
        ATENDIDO = "ATENDIDO", "Atendido"
        CANCELADO = "CANCELADO", "Cancelado"

    # Requerimiento 8: Transiciones válidas de estado.
    TRANSICIONES_VALIDAS = {
        Estado.PENDIENTE: [Estado.PREPARACION, Estado.CANCELADO],
        Estado.PREPARACION: [Estado.ATENDIDO, Estado.CANCELADO],
        Estado.ATENDIDO: [],
        Estado.CANCELADO: [],
    }

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pedidos",
    )
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    # Requerimiento 6: Controla que el stock no se devuelva más de una vez.
    stock_devuelto = models.BooleanField(default=False)

    # Requerimiento 3: Recalcular el total sumando los subtotales reales en BD.
    def recalcular_total(self):
        nuevo_total = sum(
            (detalle.subtotal for detalle in self.detalles.all()),
            Decimal("0.00"),
        )
        self.total = nuevo_total
        Pedido.objects.filter(pk=self.pk).update(total=nuevo_total)

    # Requerimientos 5, 6 y 8: Validar transición y devolver stock si se cancela.
    @transaction.atomic
    def cambiar_estado(self, nuevo_estado):
        if nuevo_estado == self.estado:
            return

        permitidos = self.TRANSICIONES_VALIDAS.get(self.estado, [])
        if nuevo_estado not in permitidos:
            etiqueta_actual = self.get_estado_display()
            etiqueta_nueva = dict(self.Estado.choices).get(nuevo_estado, nuevo_estado)
            raise ValidationError(
                f"Transición no permitida: de {etiqueta_actual} a {etiqueta_nueva}."
            )

        if nuevo_estado == self.Estado.CANCELADO and not self.stock_devuelto:
            for detalle in self.detalles.select_related("producto").all():
                Producto.objects.filter(pk=detalle.producto.pk).update(
                    stock=F("stock") + detalle.cantidad
                )
            self.stock_devuelto = True

        self.estado = nuevo_estado
        self.save(update_fields=["estado", "stock_devuelto"])

    def __str__(self):
        return f"Pedido {self.id} - {self.usuario.username}"

    class Meta:
        ordering = ["-fecha"]


# =========================================================
# MODELO DETALLE PEDIDO
# =========================================================

class DetallePedido(models.Model):

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="detalles_pedido",
    )
    cantidad = models.PositiveIntegerField(
        default=1
    )
    precio_unitario = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    # Requerimientos 2, 3 y 4: Modificar cantidades, ajustar stock y recalcular total.
    @transaction.atomic
    def actualizar_cantidad(self, nueva_cantidad):
        if self.pedido.estado != Pedido.Estado.PENDIENTE:
            raise ValidationError(
                "Solo se pueden modificar cantidades cuando el pedido está PENDIENTE."
            )

        if nueva_cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0.")

        diferencia = nueva_cantidad - self.cantidad

        if diferencia > 0:
            self.producto.refresh_from_db()
            if self.producto.stock < diferencia:
                raise ValidationError(
                    f"Stock insuficiente para {self.producto.nombre}. "
                    f"Disponible: {self.producto.stock}."
                )
            Producto.objects.filter(pk=self.producto.pk).update(
                stock=F("stock") - diferencia
            )
        elif diferencia < 0:
            Producto.objects.filter(pk=self.producto.pk).update(
                stock=F("stock") + abs(diferencia)
            )

        self.cantidad = nueva_cantidad
        self.save(update_fields=["cantidad"])
        self.pedido.recalcular_total()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.pedido.recalcular_total()

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"

    class Meta:
        verbose_name = "Detalle de pedido"
        verbose_name_plural = "Detalles de pedido"