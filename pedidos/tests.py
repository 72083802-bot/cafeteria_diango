# =========================================================
# PRUEBAS AUTOMÁTICAS
# =========================================================

# Modelo de usuario configurado por Django.
from django.contrib.auth import (
    get_user_model,
)

# Herramientas de prueba.
from django.test import TestCase

# Permite obtener URLs por su nombre.
from django.urls import reverse

# Modelo Pedido.
from .models import Pedido


# Recuperamos el modelo de usuario.
User = get_user_model()


class SeguridadSistemaTest(
    TestCase
):

    # =====================================================
    # PREPARACIÓN
    # =====================================================

    def setUp(self):

        # Usuario número 1.
        self.usuario1 = (
            User.objects.create_user(
                username="cliente01",
                password="12345678",
            )
        )

        # Usuario número 2.
        self.usuario2 = (
            User.objects.create_user(
                username="cliente02",
                password="12345678",
            )
        )

        # Administrador.
        self.admin = (
            User.objects.create_user(
                username="adminprueba",
                password="12345678",
                is_staff=True,
            )
        )

        # Pedido perteneciente al usuario 2.
        self.pedido_usuario2 = (
            Pedido.objects.create(
                usuario=self.usuario2,
                total=20,
            )
        )


    # =====================================================
    # PRUEBA 1
    # TIENDA PROTEGIDA
    # =====================================================

    def test_tienda_requiere_login(
        self
    ):

        respuesta = self.client.get(
            reverse("tienda")
        )

        # Django debe redirigir.
        self.assertEqual(
            respuesta.status_code,
            302,
        )


    # =====================================================
    # PRUEBA 2
    # NO VER PEDIDO AJENO
    # =====================================================

    def test_usuario_no_ve_pedido_ajeno(
        self
    ):

        # Iniciamos sesión como usuario1.
        self.client.login(
            username="cliente01",
            password="12345678",
        )

        respuesta = self.client.get(
            reverse(
                "detalle_pedido",
                args=[
                    self.pedido_usuario2.id
                ],
            )
        )

        # Debe devolver 404.
        self.assertEqual(
            respuesta.status_code,
            404,
        )


    # =====================================================
    # PRUEBA 3
    # REPORTES SOLO PARA STAFF
    # =====================================================

    def test_usuario_normal_no_ve_reportes(
        self
    ):

        self.client.login(
            username="cliente01",
            password="12345678",
        )

        respuesta = self.client.get(
            reverse("reportes")
        )

        # PermissionDenied devuelve 403.
        self.assertEqual(
            respuesta.status_code,
            403,
        )


    # =====================================================
    # PRUEBA 4
    # ADMINISTRADOR SÍ VE REPORTES
    # =====================================================

    def test_admin_ve_reportes(
        self
    ):

        self.client.login(
            username="adminprueba",
            password="12345678",
        )

        respuesta = self.client.get(
            reverse("reportes")
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

from decimal import Decimal
from django.core.exceptions import ValidationError
from .models import DetallePedido, Producto


class ReglasNegocioPedidoTest(TestCase):

    def setUp(self):
        self.cliente = User.objects.create_user(
            username="cliente_test",
            password="12345678",
        )
        self.admin = User.objects.create_user(
            username="admin_test",
            password="12345678",
            is_staff=True,
        )
        self.producto = Producto.objects.create(
            nombre="Café Pasado",
            precio=Decimal("10.00"),
            stock=8,
        )
        self.pedido = Pedido.objects.create(
            usuario=self.cliente,
            estado=Pedido.Estado.PENDIENTE,
        )
        self.detalle = DetallePedido.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=2,
            precio_unitario=Decimal("10.00"),
        )
        self.pedido.recalcular_total()

    def test_actualizar_cantidad_y_recalcular_total(self):
        # Aumentar cantidad de 2 a 4 -> descuenta 2 del stock (8 -> 6)
        self.detalle.actualizar_cantidad(4)
        self.producto.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(self.producto.stock, 6)
        self.assertEqual(self.pedido.total, Decimal("40.00"))

        # Disminuir cantidad de 4 a 1 -> devuelve 3 al stock (6 -> 9)
        self.detalle.actualizar_cantidad(1)
        self.producto.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(self.producto.stock, 9)
        self.assertEqual(self.pedido.total, Decimal("10.00"))

    def test_stock_insuficiente_impide_cambio(self):
        with self.assertRaises(ValidationError):
            self.detalle.actualizar_cantidad(50)

    def test_cancelar_devuelve_stock_una_sola_vez(self):
        self.pedido.cambiar_estado(Pedido.Estado.CANCELADO)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

        # Guardar nuevamente no vuelve a incrementar stock
        self.pedido.save()
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_transiciones_estado_no_permitidas(self):
        self.pedido.cambiar_estado(Pedido.Estado.PREPARACION)
        self.pedido.cambiar_estado(Pedido.Estado.ATENDIDO)
        with self.assertRaises(ValidationError):
            self.pedido.cambiar_estado(Pedido.Estado.PENDIENTE)

    def test_seguridad_usuario_normal_no_edita(self):
        self.client.login(username="cliente_test", password="12345678")
        res_editar = self.client.get(
            reverse("editar_pedido", args=[self.pedido.id])
        )
        res_estado = self.client.post(
            reverse("cambiar_estado_pedido", args=[self.pedido.id]),
            {"estado": Pedido.Estado.CANCELADO},
        )
        self.assertEqual(res_editar.status_code, 403)
        self.assertEqual(res_estado.status_code, 403)