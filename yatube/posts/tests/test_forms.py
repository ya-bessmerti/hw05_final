import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm
from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='KiberTest')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='kibertest-slug',
            description='Тестовое описание',
        )
        cls.second_group = Group.objects.create(
            title='Вторая Тестовая группа',
            slug='secondtest-slug',
            description='Тестовое описание второй группы',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовая запись через форму',
            image=uploaded,
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовая запись через форму',
            'group': self.group.pk,
            'author': self.user,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.user}),
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        last_post = Post.objects.last()
        self.assertEqual(last_post.text, form_data['text'])
        self.assertEqual(last_post.group.pk, form_data['group'])
        self.assertEqual(last_post.author, form_data['author'])
        self.assertTrue(last_post.image, form_data['image'])

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Отредактированный тестовая запись через форму',
            'group': self.second_group.pk,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            ),
        )
        self.assertEqual(Post.objects.count(), posts_count)
        edited_post = Post.objects.get(pk=self.post.pk)
        self.assertEqual(edited_post.text, form_data['text'])
        self.assertEqual(edited_post.group.pk, form_data['group'])
        self.assertEqual(edited_post.author, self.post.author)

    def test_img_context_index(self):
        """Шаблон index сформирован с картинкой."""
        response = self.authorized_client.get(reverse('posts:index'))
        post = response.context['page_obj'][0].image.name
        self.assertEqual(post, 'posts/small.gif')

    def test_img_context_profile(self):
        """Шаблон profile сформирован с картинкой."""
        response = (
            self.authorized_client.get(
                reverse(
                    'posts:profile',
                    kwargs={'username': self.user},
                )
            )
        )
        post = response.context['page_obj'][0].image.name
        self.assertEqual(post, 'posts/small.gif')

    def test_img_context_group(self):
        """Шаблон group сформирован с картинкой."""
        response = (
            self.authorized_client.get(
                reverse(
                    'posts:group_list',
                    kwargs={'slug': self.group.slug},
                )
            )
        )
        post = response.context['page_obj'][0].image.name
        self.assertEqual(post, 'posts/small.gif')

    def test_img_context_detail(self):
        """Шаблон detail сформирован с картинкой."""
        response = (
            self.authorized_client.get(
                reverse(
                    'posts:post_detail',
                    kwargs={'post_id': self.post.pk},
                )
            )
        )
        post = response.context['post'].image.name
        self.assertEqual(post, 'posts/small.gif')


class CommentFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='KiberTest')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='kibertest-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовая запись через форму',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_authorized_client_can_create_comments(self):
        """Авторизованный пользователь может комментировать посты."""
        post_count = Post.objects.count()
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Текст комментария',
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id, },
            ), data=form_data, follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            ),
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        last_comment = Comment.objects.last()
        self.assertEqual(last_comment.text, form_data['text'])
        self.assertEqual(last_comment.author, self.user)
        self.assertEqual(Post.objects.count(), post_count)


    def test_guest_client_could_not_create_comments(self):
        """Неавторизованный пользователь не может комментировать посты."""
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Текст комментария',
        }
        response = self.guest_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id, },
            ), data=form_data, follow=True
        )
        expected_redirect = str(
            reverse('users:login') + '?next=' + reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id, },
            )
        )
        self.assertRedirects(response, expected_redirect)
        self.assertEqual(Comment.objects.count(), comment_count)
