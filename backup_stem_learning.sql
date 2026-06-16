--
-- PostgreSQL database dump
--

\restrict XebZEEJCgH71QgJibQrLLB041suuSW7dldxTFzrXyLNYPrGrgcKCMLaer23P4tr

-- Dumped from database version 18.0
-- Dumped by pg_dump version 18.0

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS '';


--
-- Name: set_updated_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.set_updated_at() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: USER; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."USER" (
    user_id character varying(100) NOT NULL,
    name character varying(255),
    birth_date date,
    role_id character varying(100) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public."USER" OWNER TO postgres;

--
-- Name: class; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.class (
    class_id character varying(100) NOT NULL,
    grade integer,
    section character varying(50),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.class OWNER TO postgres;

--
-- Name: class_subject; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.class_subject (
    class_id character varying(100) NOT NULL,
    subject_id character varying(100) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.class_subject OWNER TO postgres;

--
-- Name: concept; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.concept (
    concept_id character varying(100) NOT NULL,
    metadata_id character varying(255),
    name character varying(255),
    definition text,
    file_path character varying(500),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.concept OWNER TO postgres;

--
-- Name: doc_concept; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.doc_concept (
    topic_id character varying(100) NOT NULL,
    concept_id character varying(100) NOT NULL,
    document_id character varying(100) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.doc_concept OWNER TO postgres;

--
-- Name: doc_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.doc_type (
    document_id character varying(100) NOT NULL,
    typedoc_id character varying(100) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.doc_type OWNER TO postgres;

--
-- Name: document; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.document (
    document_id character varying(100) NOT NULL,
    title character varying(255),
    file_path character varying(500),
    keysearch text,
    metadata_id character varying(255),
    content_preview text,
    order_index integer,
    page_start integer,
    page_end integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.document OWNER TO postgres;

--
-- Name: log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.log (
    log_id character varying(100) NOT NULL,
    user_id character varying(100) NOT NULL,
    doc_id character varying(100) NOT NULL,
    action character varying(100),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.log OWNER TO postgres;

--
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    role_id character varying(100) NOT NULL,
    name character varying(255),
    description text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.roles OWNER TO postgres;

--
-- Name: subject; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subject (
    subject_id character varying(100) NOT NULL,
    metadata_id character varying(255),
    name character varying(255),
    description text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.subject OWNER TO postgres;

--
-- Name: topic; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.topic (
    topic_id character varying(100) NOT NULL,
    metadata_id character varying(255),
    subject_id character varying(100) NOT NULL,
    name character varying(255),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.topic OWNER TO postgres;

--
-- Name: typedoc; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.typedoc (
    typedoc_id character varying(100) NOT NULL,
    name character varying(255),
    description text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.typedoc OWNER TO postgres;

--
-- Data for Name: USER; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public."USER" (user_id, name, birth_date, role_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: class; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.class (class_id, grade, section, created_at, updated_at) FROM stdin;
11	11	11	2026-05-29 09:33:34.990358	2026-05-29 09:33:34.990358
12	12	12	2026-05-29 09:33:38.462735	2026-05-29 09:33:38.462735
10	10	10	2026-05-29 09:33:27.869233	2026-05-29 11:50:15.853033
\.


--
-- Data for Name: class_subject; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.class_subject (class_id, subject_id, created_at, updated_at) FROM stdin;
10	VL10	2026-05-29 09:36:07.663311	2026-05-29 09:36:39.897184
10	HH10	2026-05-29 09:37:55.962413	2026-05-29 09:38:17.213259
10	TH10	2026-05-29 09:34:26.036499	2026-05-29 11:50:15.856469
\.


--
-- Data for Name: concept; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.concept (concept_id, metadata_id, name, definition, file_path, created_at, updated_at) FROM stdin;
lesson_04	META_lesson_04	Bài 4. - Hệ nhị phân và dữ liệu số nguyên	\N	STEM/10/concepts/bai-4-he-nhi-phan-va-du-lieu-so-nguyen/lesson-04.pdf	2026-05-29 09:57:44.858803	2026-05-29 10:39:51.401127
lesson_05	META_lesson_05	Bài 5. - Dữ liệu lôgic	\N	STEM/10/concepts/bai-5-du-lieu-logic/lesson-05.pdf	2026-05-29 09:57:50.271317	2026-05-29 10:39:56.797723
lesson_03	6a1900a36dce69a5eeaf7685	Bài 3. - Một số kiểu dữ liệu và dữ liệu văn bản	\N	STEM/10/concepts/bai-3-mot-so-kieu-du-lieu-va-du-lieu-van-ban/lesson-03.pdf	2026-05-29 09:57:39.239878	2026-05-29 11:50:15.845311
lesson_06	META_lesson_06	Bài 6. - Dữ liệu âm thanh và hình ảnh	\N	STEM/10/concepts/bai-6-du-lieu-am-thanh-va-hinh-anh/lesson-06.pdf	2026-05-29 09:57:56.461926	2026-05-29 10:40:02.830362
lesson_07	META_lesson_07	Bài 7. - Thực hành sử dụng thiết bị số thông dụng	\N	STEM/10/concepts/bai-7-thuc-hanh-su-dung-thiet-bi-so-thong-dung/lesson-07.pdf	2026-05-29 09:58:02.407443	2026-05-29 10:40:08.151996
lesson_08	META_lesson_08	Bài 8. - Mạng máy tính trong cuộc sống hiện đại	\N	STEM/10/concepts/bai-8-mang-may-tinh-trong-cuoc-song-hien-ai/lesson-08.pdf	2026-05-29 09:58:08.185402	2026-05-29 10:40:13.401861
lesson_09	META_lesson_09	Bài 9. - An toàn trên không gian mạng	\N	STEM/10/concepts/bai-9-an-toan-tren-khong-gian-mang/lesson-09.pdf	2026-05-29 09:58:16.209733	2026-05-29 10:40:18.829822
lesson_10	META_lesson_10	Bài 10. - Thực hành khai thác tài nguyên trên Internet	\N	STEM/10/concepts/bai-10-thuc-hanh-khai-thac-tai-nguyen-tren-internet/lesson-10.pdf	2026-05-29 09:58:23.313585	2026-05-29 10:40:24.955037
lesson_11	META_lesson_11	Bài 11. - Ứng xử trên môi trường số. Nghĩa vụ tôn trọng bản quyền	\N	STEM/10/concepts/bai-11-ung-xu-tren-moi-truong-so-nghia-vu-ton-trong-ban-quyen/lesson-11.pdf	2026-05-29 09:58:28.68798	2026-05-29 10:40:29.802429
lesson_12	META_lesson_12	Bài 12. - Phần mềm thiết kế đồ hoạ	\N	STEM/10/concepts/bai-12-phan-mem-thiet-ke-o-hoa/lesson-12.pdf	2026-05-29 09:58:35.139351	2026-05-29 10:40:35.496212
lesson_13	META_lesson_13	Bài 13. - Bổ sung các đối tượng đồ hoạ	\N	STEM/10/concepts/bai-13-bo-sung-cac-oi-tuong-o-hoa/lesson-13.pdf	2026-05-29 09:58:40.760905	2026-05-29 10:40:41.164825
lesson_14	META_lesson_14	Bài 14. - Làm việc với đối tượng đường và văn bản	\N	STEM/10/concepts/bai-14-lam-viec-voi-oi-tuong-uong-va-van-ban/lesson-14.pdf	2026-05-29 09:58:46.271877	2026-05-29 10:40:47.838125
lesson_15	META_lesson_15	Bài 15. - Hoàn thiện hình ảnh đồ hoạ	\N	STEM/10/concepts/bai-15-hoan-thien-hinh-anh-o-hoa/lesson-15.pdf	2026-05-29 09:58:52.193883	2026-05-29 10:40:53.514275
lesson_16	META_lesson_16	Bài 16. - Ngôn ngữ lập trình bậc cao và Python	\N	STEM/10/concepts/bai-16-ngon-ngu-lap-trinh-bac-cao-va-python/lesson-16.pdf	2026-05-29 09:58:58.192375	2026-05-29 10:40:58.758647
lesson_17	META_lesson_17	Bài 17. - Biến và lệnh gán	\N	STEM/10/concepts/bai-17-bien-va-lenh-gan/lesson-17.pdf	2026-05-29 09:59:04.357256	2026-05-29 10:41:03.630061
lesson_18	META_lesson_18	Bài 18. - Các lệnh vào ra đơn giản	\N	STEM/10/concepts/bai-18-cac-lenh-vao-ra-on-gian/lesson-18.pdf	2026-05-29 09:59:09.826654	2026-05-29 10:41:08.504523
lesson_19	META_lesson_19	Bài 19. - Câu lệnh rẽ nhánh if	\N	STEM/10/concepts/bai-19-cau-lenh-re-nhanh-if/lesson-19.pdf	2026-05-29 09:59:16.34521	2026-05-29 10:41:13.3225
lesson_20	META_lesson_20	Bài 20. - Câu lệnh lặp for	\N	STEM/10/concepts/bai-20-cau-lenh-lap-for/lesson-20.pdf	2026-05-29 09:59:21.626417	2026-05-29 10:41:17.779403
lesson_21	META_lesson_21	Bài 21. - Câu lệnh lặp while	\N	STEM/10/concepts/bai-21-cau-lenh-lap-while/lesson-21.pdf	2026-05-29 09:59:27.833099	2026-05-29 10:41:22.449042
lesson_22	META_lesson_22	Bài 22. - Kiểu dữ liệu danh sách	\N	STEM/10/concepts/bai-22-kieu-du-lieu-danh-sach/lesson-22.pdf	2026-05-29 09:59:33.612131	2026-05-29 10:41:27.323416
lesson_23	META_lesson_23	Bài 23. - Một số lệnh làm việc với dữ liệu danh sách	\N	STEM/10/concepts/bai-23-mot-so-lenh-lam-viec-voi-du-lieu-danh-sach/lesson-23.pdf	2026-05-29 09:59:40.640343	2026-05-29 10:41:33.46873
lesson_24	META_lesson_24	Bài 24. - Xâu kí tự	\N	STEM/10/concepts/bai-24-xau-ki-tu/lesson-24.pdf	2026-05-29 09:59:45.943648	2026-05-29 10:41:38.864163
lesson_25	META_lesson_25	Bài 25. - Một số lệnh làm việc với xâu kí tự	\N	STEM/10/concepts/bai-25-mot-so-lenh-lam-viec-voi-xau-ki-tu/lesson-25.pdf	2026-05-29 09:59:51.242084	2026-05-29 10:41:43.976079
lesson_26	META_lesson_26	Bài 26. - Hàm trong Python	\N	STEM/10/concepts/bai-26-ham-trong-python/lesson-26.pdf	2026-05-29 09:59:56.428768	2026-05-29 10:41:48.730655
lesson_27	META_lesson_27	Bài 27. - Tham số của hàm	\N	STEM/10/concepts/bai-27-tham-so-cua-ham/lesson-27.pdf	2026-05-29 10:00:01.932159	2026-05-29 10:41:53.879707
lesson_28	META_lesson_28	Bài 28. - Phạm vi của biến	\N	STEM/10/concepts/bai-28-pham-vi-cua-bien/lesson-28.pdf	2026-05-29 10:00:07.885619	2026-05-29 10:41:58.858866
lesson_29	META_lesson_29	Bài 29. - Nhận biết lỗi chương trình	\N	STEM/10/concepts/bai-29-nhan-biet-loi-chuong-trinh/lesson-29.pdf	2026-05-29 10:00:13.591876	2026-05-29 10:42:03.491555
lesson_30	META_lesson_30	Bài 30. - Kiểm thử và gỡ lỗi chương trình	\N	STEM/10/concepts/bai-30-kiem-thu-va-go-loi-chuong-trinh/lesson-30.pdf	2026-05-29 10:00:18.844716	2026-05-29 10:42:08.430501
lesson_31	META_lesson_31	Bài 31. - Thực hành viết chương trình đơn giản	\N	STEM/10/concepts/bai-31-thuc-hanh-viet-chuong-trinh-on-gian/lesson-31.pdf	2026-05-29 10:00:24.558877	2026-05-29 10:42:13.702746
lesson_32	META_lesson_32	Bài 32. - Ôn tập lập trình Python	\N	STEM/10/concepts/bai-32-on-tap-lap-trinh-python/lesson-32.pdf	2026-05-29 10:00:29.935399	2026-05-29 10:42:18.236334
lesson_33	META_lesson_33	Bài 33. - Nghề thiết kế đồ hoạ máy tính	\N	STEM/10/concepts/bai-33-nghe-thiet-ke-o-hoa-may-tinh/lesson-33.pdf	2026-05-29 10:00:35.682573	2026-05-29 10:42:24.686722
lesson_34	META_lesson_34	Bài 34. - Nghề phát triển phần mềm	\N	STEM/10/concepts/bai-34-nghe-phat-trien-phan-mem/lesson-34.pdf	2026-05-29 10:00:40.8906	2026-05-29 10:42:29.072055
lesson_02	META_lesson_02	Bài 2. - Vai trò của thiết bị thông minh và tin học đối với xã hội	\N	STEM/10/concepts/bai-2-vai-tro-cua-thiet-bi-thong-minh-va-tin-hoc-oi-voi-xa-hoi/lesson-02.pdf	2026-05-29 09:57:33.471802	2026-05-29 10:45:36.884702
lesson_01	META_lesson_01	Bài 1. - Thông tin và xử lí thông tin	\N	STEM/10/concepts/bai-1-thong-tin-va-xu-li-thong-tin/lesson-01.pdf	2026-05-29 09:57:27.531002	2026-05-29 11:11:13.115613
\.


--
-- Data for Name: doc_concept; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.doc_concept (topic_id, concept_id, document_id, created_at, updated_at) FROM stdin;
topic_01	lesson_02	lesson_02_chunk_01	2026-05-29 10:45:29.767106	2026-05-29 10:45:29.767106
topic_01	lesson_02	lesson_02_chunk_02	2026-05-29 10:45:36.891652	2026-05-29 10:45:36.891652
topic_01	lesson_01	lesson_01_chunk_01	2026-05-29 10:19:10.264035	2026-05-29 11:11:10.726728
topic_01	lesson_01	lesson_01_chunk_02	2026-05-29 10:19:16.22399	2026-05-29 11:11:12.648788
topic_01	lesson_01	lesson_01_chunk_03	2026-05-29 10:19:22.19128	2026-05-29 11:11:13.130588
topic_01	lesson_03	lesson_03_chunk_01	2026-05-29 10:46:20.341328	2026-05-29 11:50:13.886666
topic_01	lesson_03	lesson_03_chunk_02	2026-05-29 10:46:26.657619	2026-05-29 11:50:15.861847
\.


--
-- Data for Name: doc_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.doc_type (document_id, typedoc_id, created_at, updated_at) FROM stdin;
lesson_02_chunk_01	pdf	2026-05-29 10:45:29.783471	2026-05-29 10:45:29.783471
lesson_02_chunk_02	pdf	2026-05-29 10:45:36.896076	2026-05-29 10:45:36.896076
lesson_01_chunk_01	pdf	2026-05-29 10:19:10.27324	2026-05-29 11:11:10.738395
lesson_01_chunk_02	pdf	2026-05-29 10:19:16.230218	2026-05-29 11:11:12.654635
lesson_01_chunk_03	pdf	2026-05-29 10:19:22.203165	2026-05-29 11:11:13.140532
lesson_03_chunk_01	pdf	2026-05-29 10:46:20.352594	2026-05-29 11:50:13.897636
lesson_03_chunk_02	pdf	2026-05-29 10:46:26.66895	2026-05-29 11:50:15.869696
\.


--
-- Data for Name: document; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.document (document_id, title, file_path, keysearch, metadata_id, content_preview, order_index, page_start, page_end, created_at, updated_at) FROM stdin;
lesson_02_chunk_01	1. THIẾT BỊ THÔNG MINH	STEM/10/documents/1-thiet-bi-thong-minh/chunk-01.pdf	\N	META_lesson_02_chunk_01	\N	1	12	14	2026-05-29 10:45:29.762593	2026-05-29 10:45:29.762593
lesson_02_chunk_02	2. CÁC THÀNH TỰU CỦA TIN HỌC	STEM/10/documents/2-cac-thanh-tuu-cua-tin-hoc/chunk-02.pdf	\N	META_lesson_02_chunk_02	\N	2	14	16	2026-05-29 10:45:36.891142	2026-05-29 10:45:36.891142
lesson_01_chunk_01	1. THÔNG TIN VÀ DỮ LIỆU	STEM/10/documents/1-thong-tin-va-du-lieu/chunk-01.pdf	Thông tin, Dữ liệu, Quá trình xử lí thông tin, Tiếp nhận dữ liệu, Xử lí dữ liệu	META_lesson_01_chunk_01	\N	1	7	9	2026-05-29 10:19:10.261062	2026-05-29 11:11:10.725414
lesson_01_chunk_02	2. ĐƠN VỊ LƯU TRỮ DỮ LIỆU	STEM/10/documents/2-on-vi-luu-tru-du-lieu/chunk-02.pdf	Đơn vị lưu trữ dữ liệu, Byte, bit, 2^10 = 1024, Kilobyte	META_lesson_01_chunk_02	\N	2	9	10	2026-05-29 10:19:16.223207	2026-05-29 11:11:12.64804
lesson_01_chunk_03	3. LƯU TRỮ, XỬ LÍ VÀ TRUYỀN THÔNG BẰNG THIẾT BỊ SỐ	STEM/10/documents/3-luu-tru-xu-li-va-truyen-thong-bang-thiet-bi-so/chunk-03.pdf	Thiết bị số, Lưu trữ thông tin, Xử lí thông tin, Truyền thông, Internet	META_lesson_01_chunk_03	\N	3	10	11	2026-05-29 10:19:22.190653	2026-05-29 11:11:13.129755
lesson_03_chunk_01	1. PHÂN LOẠI VÀ BIỂU DIỄN THÔNG TIN TRONG MÁY TÍNH	STEM/10/documents/1-phan-loai-va-bieu-dien-thong-tin-trong-may-tinh/chunk-01.pdf	Phân loại dữ liệu, Biểu diễn thông tin, Dữ liệu, Kiểu dữ liệu, Dữ liệu nhị phân	6a190c0b6dce69a5eeaf76ba	\N	1	17	18	2026-05-29 10:46:20.340789	2026-05-29 11:50:13.88431
lesson_03_chunk_02	2. BIỂU DIỄN DỮ LIỆU VĂN BẢN	STEM/10/documents/2-bieu-dien-du-lieu-van-ban/chunk-02.pdf	BIỂU DIỄN DỮ LIỆU VĂN BẢN, Bảng mã ASCII, Bảng mã Unicode, UTF-8, Số hoá văn bản	6a190c126dce69a5eeaf76be	\N	2	18	20	2026-05-29 10:46:26.656685	2026-05-29 11:50:15.85963
\.


--
-- Data for Name: log; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.log (log_id, user_id, doc_id, action, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.roles (role_id, name, description, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: subject; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.subject (subject_id, metadata_id, name, description, created_at, updated_at) FROM stdin;
VL10	META_VL10	Lý 10	string	2026-05-29 09:36:07.662997	2026-05-29 09:36:39.896755
HH10	META_HH10	Hóa 10	string	2026-05-29 09:37:55.959718	2026-05-29 09:38:17.212811
TH10	6a18fb310f8bb31c38795812	Tin 10	string	2026-05-29 09:34:26.030077	2026-05-29 11:50:15.855781
\.


--
-- Data for Name: topic; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.topic (topic_id, metadata_id, subject_id, name, created_at, updated_at) FROM stdin;
topic_01	6a18ff1a6dce69a5eeaf767d	TH10	MÁY TÍNH VÀ XÃ HỘI TRI THỨC	2026-05-29 09:51:08.19068	2026-05-29 11:50:15.858094
topic_05	META_topic_05	TH10	GIẢI QUYẾT VẤN ĐỀ VỚI SỰ TRỢ GIÚP CỦA MÁY TÍNH	2026-05-29 09:51:40.060625	2026-05-29 10:42:18.245335
topic_06	META_topic_06	TH10	HƯỚNG NGHIỆP VỚI TIN HỌC	2026-05-29 09:51:47.557394	2026-05-29 10:42:29.078682
topic_02	META_topic_02	TH10	MẠNG MÁY TÍNH VÀ INTERNET	2026-05-29 09:51:17.384953	2026-05-29 10:40:24.967315
topic_03	META_topic_03	TH10	ĐẠO ĐỨC, PHÁP LUẬT VÀ VĂN HOÁ TRONG MÔI TRƯỜNG SỐ	2026-05-29 09:51:23.128488	2026-05-29 10:40:29.815957
topic_04	META_topic_04	TH10	ỨNG DỤNG TIN HỌC	2026-05-29 09:51:32.689807	2026-05-29 10:40:53.525914
\.


--
-- Data for Name: typedoc; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.typedoc (typedoc_id, name, description, created_at, updated_at) FROM stdin;
pdf	pdf	Auto-created from MongoDB documents.typedocs field	2026-05-29 10:19:10.270223	2026-05-29 11:50:15.865602
\.


--
-- Name: USER USER_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."USER"
    ADD CONSTRAINT "USER_pkey" PRIMARY KEY (user_id);


--
-- Name: class class_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.class
    ADD CONSTRAINT class_pkey PRIMARY KEY (class_id);


--
-- Name: class_subject class_subject_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.class_subject
    ADD CONSTRAINT class_subject_pkey PRIMARY KEY (class_id, subject_id);


--
-- Name: concept concept_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.concept
    ADD CONSTRAINT concept_pkey PRIMARY KEY (concept_id);


--
-- Name: doc_concept doc_concept_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.doc_concept
    ADD CONSTRAINT doc_concept_pkey PRIMARY KEY (topic_id, concept_id, document_id);


--
-- Name: doc_type doc_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.doc_type
    ADD CONSTRAINT doc_type_pkey PRIMARY KEY (document_id, typedoc_id);


--
-- Name: document document_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document
    ADD CONSTRAINT document_pkey PRIMARY KEY (document_id);


--
-- Name: log log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.log
    ADD CONSTRAINT log_pkey PRIMARY KEY (log_id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (role_id);


--
-- Name: subject subject_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subject
    ADD CONSTRAINT subject_pkey PRIMARY KEY (subject_id);


--
-- Name: topic topic_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic
    ADD CONSTRAINT topic_pkey PRIMARY KEY (topic_id);


--
-- Name: typedoc typedoc_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.typedoc
    ADD CONSTRAINT typedoc_pkey PRIMARY KEY (typedoc_id);


--
-- Name: idx_concept_metadata_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_concept_metadata_id ON public.concept USING btree (metadata_id);


--
-- Name: idx_doc_concept_concept_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_doc_concept_concept_id ON public.doc_concept USING btree (concept_id);


--
-- Name: idx_doc_concept_document_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_doc_concept_document_id ON public.doc_concept USING btree (document_id);


--
-- Name: idx_doc_concept_topic_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_doc_concept_topic_id ON public.doc_concept USING btree (topic_id);


--
-- Name: idx_document_metadata_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_document_metadata_id ON public.document USING btree (metadata_id);


--
-- Name: idx_subject_metadata_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_subject_metadata_id ON public.subject USING btree (metadata_id);


--
-- Name: idx_topic_metadata_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_topic_metadata_id ON public.topic USING btree (metadata_id);


--
-- Name: idx_topic_subject_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_topic_subject_id ON public.topic USING btree (subject_id);


--
-- Name: class_subject trg_class_subject_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_class_subject_updated_at BEFORE UPDATE ON public.class_subject FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: class trg_class_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_class_updated_at BEFORE UPDATE ON public.class FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: concept trg_concept_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_concept_updated_at BEFORE UPDATE ON public.concept FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: doc_concept trg_doc_concept_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_doc_concept_updated_at BEFORE UPDATE ON public.doc_concept FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: doc_type trg_doc_type_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_doc_type_updated_at BEFORE UPDATE ON public.doc_type FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: document trg_document_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_document_updated_at BEFORE UPDATE ON public.document FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: log trg_log_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_log_updated_at BEFORE UPDATE ON public.log FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: roles trg_roles_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_roles_updated_at BEFORE UPDATE ON public.roles FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: subject trg_subject_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_subject_updated_at BEFORE UPDATE ON public.subject FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: topic trg_topic_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_topic_updated_at BEFORE UPDATE ON public.topic FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: typedoc trg_typedoc_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_typedoc_updated_at BEFORE UPDATE ON public.typedoc FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: USER trg_user_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_user_updated_at BEFORE UPDATE ON public."USER" FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: USER USER_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."USER"
    ADD CONSTRAINT "USER_role_id_fkey" FOREIGN KEY (role_id) REFERENCES public.roles(role_id);


--
-- Name: class_subject class_subject_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.class_subject
    ADD CONSTRAINT class_subject_class_id_fkey FOREIGN KEY (class_id) REFERENCES public.class(class_id);


--
-- Name: class_subject class_subject_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.class_subject
    ADD CONSTRAINT class_subject_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(subject_id);


--
-- Name: doc_concept doc_concept_concept_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.doc_concept
    ADD CONSTRAINT doc_concept_concept_id_fkey FOREIGN KEY (concept_id) REFERENCES public.concept(concept_id);


--
-- Name: doc_concept doc_concept_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.doc_concept
    ADD CONSTRAINT doc_concept_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.document(document_id);


--
-- Name: doc_concept doc_concept_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.doc_concept
    ADD CONSTRAINT doc_concept_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.topic(topic_id);


--
-- Name: doc_type doc_type_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.doc_type
    ADD CONSTRAINT doc_type_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.document(document_id);


--
-- Name: doc_type doc_type_typedoc_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.doc_type
    ADD CONSTRAINT doc_type_typedoc_id_fkey FOREIGN KEY (typedoc_id) REFERENCES public.typedoc(typedoc_id);


--
-- Name: log log_doc_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.log
    ADD CONSTRAINT log_doc_id_fkey FOREIGN KEY (doc_id) REFERENCES public.document(document_id);


--
-- Name: log log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.log
    ADD CONSTRAINT log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."USER"(user_id);


--
-- Name: topic topic_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic
    ADD CONSTRAINT topic_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(subject_id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

\unrestrict XebZEEJCgH71QgJibQrLLB041suuSW7dldxTFzrXyLNYPrGrgcKCMLaer23P4tr

