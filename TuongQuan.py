import streamlit as st
import pandas as pd
import mysql.connector
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from datetime import datetime, timedelta

# Giao diện Streamlit
hide_st_style = """
<style>
    .block-container {
        padding-top: 0rem;  /* Giảm khoảng cách phía trên */
        padding-left: 1rem;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton > button {
        width: 100%; /* Chiều rộng bằng 100% của sidebar */
    }
</style>
"""
st.set_page_config(
    page_title="Trực quan hóa dữ liệu quan trắc than tự cháy",
    layout="wide",
    page_icon="✅",
    initial_sidebar_state="expanded",
)

#st.markdown("<h1 style='color:#5192e0;'>💻Phân tích dữ liệu than tự cháy mỏ hầm lò</h1>", unsafe_allow_html=True)
st.markdown(hide_st_style, unsafe_allow_html=True)

# Định nghĩa các ngưỡng cảnh báo
nguong_nhiet_do_thap = 40  # Ngưỡng cảnh báo thấp cho nhiệt độ (°C)
nguong_nhiet_do_cao = 50   # Ngưỡng cảnh báo cao cho nhiệt độ (°C)
nguong_co_thap = 17        # Ngưỡng cảnh báo thấp cho hàm lượng CO (ppm)
nguong_co_cao = 34         # Ngưỡng cảnh báo cao cho hàm lượng CO (ppm)
nguong_o2_thap = 18.5      # Ngưỡng cảnh báo thấp cho hàm lượng O2 (%)
nguong_o2_cao = 19.5       # Ngưỡng cảnh báo cao cho hàm lượng O2 (%)

kiemtra_thoigian = False

# Kết nối tới cơ sở dữ liệu MySQL
def get_data(start_date, end_date, selected_columns):
    conn = mysql.connector.connect(
        host="123.24.206.17",
        port="3306",
        user="admin",
        password="elatec123!",
        database="thantuchay"
    )
    columns_str = ', '.join(selected_columns)
    query = f"""
    SELECT date_time, {columns_str}
    FROM dulieuhalong
    WHERE date_time >= '{start_date}' AND date_time <= '{end_date}'
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Khung chọn thời gian
with st.sidebar.expander("⚙️Chọn thời gian", expanded=True):
    start_date = st.date_input("📅Chọn ngày bắt đầu")  # Bỏ giá trị mặc định
    start_time = st.time_input("⏰Chọn giờ bắt đầu")  # Bỏ giá trị mặc định

    end_date = st.date_input("📅Chọn ngày kết thúc")  # Bỏ giá trị mặc định
    end_time = st.time_input("⏰Chọn giờ kết thúc")  # Bỏ giá trị mặc định

# Kiểm tra xem người dùng đã chọn giá trị hay chưa
if start_date and start_time and end_date and end_time:
    # Chuyển đổi thành chuỗi sau khi người dùng chọn giá trị
    start_datetime = f"{start_date} {start_time}"
    end_datetime = f"{end_date} {end_time}"

    # Chuyển đổi chuỗi thành đối tượng datetime
    start_datetime_check = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
    end_datetime_check = datetime.strptime(end_datetime, "%Y-%m-%d %H:%M:%S")
    # Kiểm tra nếu end_datetime_check lớn hơn start_datetime_check
    if end_datetime_check < start_datetime_check:
        st.sidebar.error("🤭Thời gian kết thúc phải lớn hơn thời gian bắt đầu!")
    else:
        kiemtra_thoigian = True
else:
    st.sidebar.warning("👩‍🔧Vui lòng chọn đầy đủ ngày và giờ.")

# Nhóm các thông số
khu_vuc = {
    "Tủ 1 khu 1": ["NhietDo1Tram1", "Co1Tram1", "Oxy1Tram1"],
    "Tủ 1 khu 2": ["NhietDo2Tram1", "Co2Tram1", "Oxy2Tram1"],
    "Tủ 2 khu 1": ["NhietDo1Tram2", "Co1Tram2", "Oxy1Tram2"],
    "Tủ 2 khu 2": ["NhietDo2Tram2", "Co2Tram2", "Oxy2Tram2"]
}

# Khung chọn thông số và các nút vẽ biểu đồ
with st.sidebar.expander("🌎Chọn thông số để vẽ biểu đồ", expanded=True):
    all_columns = [col for khu in khu_vuc.values() for col in khu]
    selected_columns = st.multiselect(
        "Nhấn mũi tên chọn thông số👇",
        all_columns,
        default=["NhietDo1Tram1"]
    )

# Khung chọn khu vực để vẽ bản đồ nhiệt
with st.sidebar.expander("🗺️Chọn khu vực để vẽ biểu đồ", expanded=True):
    selected_khu_vuc = st.multiselect(
        "Nhấn mũi tên chọn khu vực👇",
        list(khu_vuc.keys()),
        default=["Tủ 1 khu 1"]
    )

# Nút nhấn để đọc dữ liệu và vẽ biểu đồ
if st.sidebar.button("📊Vẽ biểu đồ và phân tích thông số"):
    # Kiểm tra xem người dùng đã chọn thời gian và thông số hay chưa
    if not kiemtra_thoigian or not selected_columns:
        st.warning("🤭Vui lòng chọn đầy đủ thời gian và thông số. Thời gian kết thúc phải lớn hơn thời gian bắt đầu!")
    else:
        with st.spinner('⌛Đang tải dữ liệu...'):
            df = get_data(start_datetime, end_datetime, selected_columns)
            if not df.empty:
                df.fillna(df.mean(), inplace=True)  # Thay thế giá trị NULL bằng trung bình
                df['date_time'] = pd.to_datetime(df['date_time'])  # Chuyển đổi cột thời gian
                df.set_index('date_time', inplace=True)
                #Bieu do duong
                for column in selected_columns:
                    if 'NhietDo' in column:
                        y_range = [0, 100]
                        y_title = 'Nhiệt độ (°C)'
                        x_title = 'Thời gian'
                        temp = "nhiệt độ"
                        donvi = "°C"
                        nguong_thap = nguong_nhiet_do_thap
                        nguong_cao = nguong_nhiet_do_cao
                    elif 'Co' in column:
                        y_range = [0, 50]
                        y_title = 'Hàm lượng CO (ppm)'
                        x_title = 'Thời gian'
                        temp = "hàm lượng CO"
                        donvi = "ppm"
                        nguong_thap = nguong_co_thap
                        nguong_cao = nguong_co_cao
                    elif 'Oxy' in column:
                        y_range = [0, 30]
                        y_title = 'Hàm lượng O2 (%)'
                        x_title = 'Thời gian'
                        temp = "hàm lượng O2"
                        donvi = "%"
                        nguong_thap = nguong_o2_thap
                        nguong_cao = nguong_o2_cao

                    st.write(f"<h3 style='color: #34dbac;'>💠 Biểu đồ đường {temp} theo thời gian</h3>", unsafe_allow_html=True)

                    # Tạo layout với hai cột
                    col1, col2 = st.columns([2, 1])

                    # Biểu đồ ở cột bên trái
                    with col1:
                        fig_line = px.line(df, x=df.index, y=column)
                        fig_line.update_xaxes(title_text=x_title)
                        fig_line.update_yaxes(title_text=y_title)
                        fig_line.update_layout(showlegend=False)
                        st.plotly_chart(fig_line)

                    # Giải thích ở cột bên phải
                    with col2:
                        max_val = df[column].max()
                        min_val = df[column].min()

                        st.markdown("📚Giải thích")
                        st.write(f"📊Biểu đồ đường thể hiện sự biến động của {temp} theo thời gian.")

                        if 'NhietDo' in column:
                            if max_val > nguong_cao:
                                st.write(f"⚠️Nhiệt độ vượt quá ngưỡng nguy hiểm ({nguong_cao} {donvi}). Cần kiểm tra ngay lập tức!")
                                time_over_threshold = df[df[column] > nguong_cao].index
                                if len(time_over_threshold) > 0:
                                    st.write(f"📌Thời gian vượt ngưỡng: {time_over_threshold}")
                            elif max_val > nguong_thap:
                                st.write(f"❗Nhiệt độ vượt quá ngưỡng cảnh báo ({nguong_thap} {donvi}). Cần theo dõi chặt chẽ.")
                            else:
                                st.write(f"🤩Nhiệt độ nằm trong mức an toàn, cho thấy nguy cơ tự cháy than ở mức thấp.")
                            st.write(f"🔴Nhiệt độ cao nhất: {max_val:.1f} {donvi}")
                            st.write(f"🔵Nhiệt độ thấp nhất: {min_val:.1f} {donvi}")

                            # Phân tích thêm (ví dụ: xu hướng)
                            #st.write("🚀Phân tích sâu")
                            diff = df[column].diff()
                            # 2. Phân tích biến động
                            # std = df[column].std()
                            # if std > 0.5:  # Điều chỉnh ngưỡng tùy theo dữ liệu
                            #     st.write(f"🏹Biến động: {temp} có biến động lớn (độ lệch chuẩn: {std:.2f}).")
                            # else:
                            #     st.write(f"⚖️Biến động: {temp} có biến động nhỏ (độ lệch chuẩn: {std:.2f}).")

                            # 3. Phân tích các yếu tố khác (ví dụ: thời gian đạt giá trị cao nhất/thấp nhất)
                            max_time = df[column].idxmax()
                            min_time = df[column].idxmin()
                            st.write(f"🕔Thời gian đạt giá trị cao nhất: {max_time}")
                            st.write(f"🕗Thời gian đạt giá trị thấp nhất: {min_time}")

                            # 4. Phân tích các yếu tố đặc biệt (ví dụ: đột biến)
                            diff_abs = abs(diff)
                            if (diff_abs > 5).sum() > 0:  # Điều chỉnh ngưỡng tùy theo dữ liệu
                                st.write(f"📌Có đột biến trong dữ liệu {temp}.")
                            # # 1. Xác định xu hướng
                            # if (diff > 0).sum() > (diff < 0).sum():
                            #     st.write(f"📈Xu hướng: Nhiệt độ có xu hướng tăng, cho thấy nguy cơ than tự cháy ở mức cần phải theo dõi cẩn thận!")
                            # elif (diff < 0).sum() > (diff > 0).sum():
                            #     st.write(f"📉Xu hướng: Nhiệt độ có xu hướng giảm, cho thấy nguy cơ than tự cháy ở mức an toàn tuy nhiên vẫn cần tiếp tục theo dõi.")
                            # else:
                            #     st.write(f"📊Xu hướng: Nhiệt độ không có xu hướng rõ ràng, cho thấy nguy cơ than tự cháy ở mức khá an toàn tuy nhiên cần tiếp tục theo dõi.")


                        # elif 'Co' in column:
                        #     if max_val > nguong_cao:
                        #         st.write(f"⚠️Hàm lượng CO vượt quá ngưỡng nguy hiểm ({nguong_cao} {donvi}). Cần kiểm tra ngay lập tức!")
                        #         time_over_threshold = df[df[column] > nguong_cao].index
                        #         if len(time_over_threshold) > 0:
                        #             st.write(f"📌Thời gian vượt ngưỡng: {time_over_threshold}")
                        #             if len(time_over_threshold) == 1:
                        #                 time_diff = time_over_threshold[0] - df.index[df[column] > nguong_cao].index[0]
                        #                 if time_diff.total_seconds() < 30:
                        #                     st.write("🧨Hàm lượng khí CO vừa tăng cao nhưng rồi giảm ngay, cho thấy nguy cơ tự cháy than ở mức khá an toàn tuy nhiên cần tiếp tục theo dõi. Hiện tượng này do bắn mìn dưới hầm lò.")
                        #     elif max_val > nguong_thap:
                        #         st.write(f"❗Hàm lượng CO vượt quá ngưỡng cảnh báo ({nguong_thap} {donvi}). Cần theo dõi chặt chẽ.")
                        #         time_over_threshold = df[df[column] > nguong_thap].index
                        #         if len(time_over_threshold) > 0:
                        #             #st.write(f"📌Thời gian vượt ngưỡng: {time_over_threshold}")
                        #
                        #             if len(time_over_threshold) >= 1:
                        #                 for i, time_point in enumerate(time_over_threshold):
                        #                     st.write(f"Thời điểm vượt ngưỡng thứ {i + 1}: {time_point}")
                        #                     time_diff = time_over_threshold[i + 1] - df.index[df[column] > nguong_thap].index[i + 1]
                        #                     if time_diff.total_seconds() < 30:
                        #                         st.write("🧨Hàm lượng khí CO vừa tăng cao nhưng rồi giảm ngay, cho thấy nguy cơ tự cháy than ở mức khá an toàn tuy nhiên cần tiếp tục theo dõi. Hiện tượng này do bắn mìn dưới hầm lò.")
                        #     else:
                        #         st.write(f"🤩Hàm lượng CO nằm trong mức an toàn.")
                        #     st.write(f"🔴Hàm lượng CO cao nhất: {max_val:.1f} {donvi}")
                        #     st.write(f"🔵Hàm lượng CO thấp nhất: {min_val:.1f} {donvi}")
                        elif 'Co' in column:
                            # 1. Xác định xu hướng
                            diff = df[column].diff()
                            if (diff > 0).sum() > (diff < 0).sum():
                                st.write(f"📈Xu hướng: {temp} có xu hướng tăng.")
                                if max_val > nguong_co_cao:
                                    st.write("🧨Hàm lượng khí CO tăng rất cao và có xu hướng tăng, cho thấy nguy cơ tự cháy than ở mức cần kiểm tra theo dõi và có phương án phòng ngừa.")
                                elif max_val > nguong_co_thap:
                                    st.write("🧨Hàm lượng khí CO tăng cao và có xu hướng tăng, cho thấy nguy cơ tự cháy than ở mức cần kiểm tra theo dõi.")
                            elif (diff < 0).sum() > (diff > 0).sum():
                                st.write(f"📉Xu hướng: {temp} có xu hướng giảm.")
                                if max_val > nguong_co_cao:
                                    st.write("🧨Hàm lượng khí CO tăng rất cao và có xu hướng giảm, cho thấy nguy cơ tự cháy than ở mức thấp. Hiện tượng này do bắn mìn dưới hầm lò.")
                                elif max_val > nguong_co_thap:
                                    st.write("🧨Hàm lượng khí CO tăng cao và có xu hướng giảm, cho thấy nguy cơ tự cháy than ở mức thấp. Hiện tượng này do bắn mìn dưới hầm lò.")
                            else:
                                st.write(f"⚖️Xu hướng: {temp} không có xu hướng rõ ràng.")
                                if max_val > nguong_co_cao:
                                    st.write("🧨Hàm lượng khí CO tăng rất cao nhưng rồi giảm ngay, cho thấy nguy cơ tự cháy than ở mức thấp tuy nhiên cần tiếp tục theo dõi. Hiện tượng này do bắn mìn dưới hầm lò.")
                                elif max_val > nguong_co_thap:
                                    st.write("🧨Hàm lượng khí CO tăng cao nhưng rồi giảm ngay, cho thấy nguy cơ tự cháy than ở mức thấp tuy nhiên cần tiếp tục theo dõi. Hiện tượng này do bắn mìn dưới hầm lò.")
                            if max_val > nguong_cao:
                                st.write(
                                    f"⚠️Hàm lượng CO vượt quá ngưỡng nguy hiểm ({nguong_cao} {donvi}). Cần kiểm tra, theo dõi!")

                            elif max_val > nguong_thap:
                                st.write(
                                    f"❗Hàm lượng CO vượt quá ngưỡng cảnh báo ({nguong_thap} {donvi}). Cần theo dõi chặt chẽ.")
                            else:
                                st.write(f"🤩Hàm lượng CO nằm trong mức an toàn, cho thấy nguy cơ tự cháy than ở mức thấp.")
                                st.write(f"🔴Hàm lượng CO cao nhất: {max_val:.1f} {donvi}")
                                st.write(f"🔵Hàm lượng CO thấp nhất: {min_val:.1f} {donvi}")

                            # Phân tích thêm (ví dụ: xu hướng)
                            # st.write("🚀Phân tích sâu")
                            diff = df[column].diff()
                            # 2. Phân tích biến động
                            # std = df[column].std()
                            # if std > 0.5:  # Điều chỉnh ngưỡng tùy theo dữ liệu
                            #     st.write(f"🏹Biến động: {temp} có biến động lớn (độ lệch chuẩn: {std:.2f}).")
                            # else:
                            #     st.write(f"⚖️Biến động: {temp} có biến động nhỏ (độ lệch chuẩn: {std:.2f}).")

                            # 3. Phân tích các yếu tố khác (ví dụ: thời gian đạt giá trị cao nhất/thấp nhất)
                            max_time = df[column].idxmax()
                            min_time = df[column].idxmin()
                            st.write(f"🕔Thời gian đạt giá trị cao nhất: {max_time}")
                            st.write(f"🕗Thời gian đạt giá trị thấp nhất: {min_time}")

                            # 4. Phân tích các yếu tố đặc biệt (ví dụ: đột biến)
                            diff_abs = abs(diff)
                            if (diff_abs > 5).sum() > 0:  # Điều chỉnh ngưỡng tùy theo dữ liệu
                                st.write(f"📌Có đột biến trong dữ liệu {temp}.")
                            # 1. Xác định xu hướng
                            # if (diff > 0).sum() > (diff < 0).sum():
                            #     st.write(f"📈Xu hướng: Hàm lượng CO có xu hướng tăng, cho thấy nguy cơ than tự cháy ở mức cần phải theo dõi cẩn thận!")
                            # elif (diff < 0).sum() > (diff > 0).sum():
                            #     st.write(f"📉Xu hướng: Hàm lượng CO có xu hướng giảm, cho thấy nguy cơ than tự cháy ở mức an toàn tuy nhiên vẫn cần tiếp tục theo dõi.")
                            # else:
                            #     st.write(f"📊Xu hướng: Hàm lượng CO không có xu hướng rõ ràng, cho thấy nguy cơ than tự cháy ở mức khá an toàn tuy nhiên cần tiếp tục theo dõi.")
                        elif 'Oxy' in column:
                            # if 0 < min_val < nguong_thap:
                            #     st.write(f"⚠️Hàm lượng O2 thấp hơn ngưỡng nguy hiểm ({nguong_thap} {donvi}). Nguy hiểm cho hô hấp! Cần kiểm tra ngay lập tức!")
                            # if 0 < max_val < nguong_cao:
                            #     st.write(f"❗Hàm lượng O2 thấp hơn ngưỡng nguy hiểm ({nguong_cao} {donvi}). Cần kiểm tra theo dõi.")
                            # else:
                            #     st.write(f"🤩Hàm lượng O2 nằm trong mức an toàn.")
                            #
                            # st.write(f"🔵Hàm lượng O2 cao nhất: {max_val:.1f} {donvi}")
                            # st.write(f"🔴Hàm lượng O2 thấp nhất: {min_val:.1f} {donvi}")

                            # Phân tích thêm (ví dụ: xu hướng)
                            st.write("🚀Phân tích sâu")
                            diff = df[column].diff()
                            # 2. Phân tích biến động
                            # std = df[column].std()
                            # if std > 0.5:  # Điều chỉnh ngưỡng tùy theo dữ liệu
                            #     st.write(f"🏹Biến động: {temp} có biến động lớn (độ lệch chuẩn: {std:.2f}).")
                            # else:
                            #     st.write(f"⚖️Biến động: {temp} có biến động nhỏ (độ lệch chuẩn: {std:.2f}).")

                            # 3. Phân tích các yếu tố khác (ví dụ: thời gian đạt giá trị cao nhất/thấp nhất)
                            max_time = df[column].idxmax()
                            min_time = df[column].idxmin()
                            st.write(f"🕔Thời gian đạt giá trị cao nhất: {max_time}")
                            st.write(f"🕗Thời gian đạt giá trị thấp nhất: {min_time}")

                            # 4. Phân tích các yếu tố đặc biệt (ví dụ: đột biến)
                            diff_abs = abs(diff)
                            if (diff_abs > 5).sum() > 0:  # Điều chỉnh ngưỡng tùy theo dữ liệu
                                if min_val == 0:
                                    st.write(f"📌Có đột biến trong dữ liệu {temp}, lúc: {min_time}. Có thể do mất điện của tủ phòng nổ, hãy kiểm tra cảnh báo trên phần mềm WinScada máy tính.")
                                else:
                                    st.write(f"📌Có đột biến trong dữ liệu {temp}. Cần kiểm tra theo dõi.")
                            # 1. Xác định xu hướng
                            # if (diff > 0).sum() > (diff < 0).sum():
                            #     st.write(
                            #         f"📈Xu hướng: Hàm lượng ôxy có xu hướng tăng, cho thấy nguy cơ than tự cháy ở mức an toàn tuy nhiên cần tiếp tục theo dõi.")
                            # elif (diff < 0).sum() > (diff > 0).sum():
                            #     st.write(
                            #         f"📉Xu hướng: Hàm lượng ôxy có xu hướng giảm, cần phải theo dõi cẩn thận về nguy cơ than tự cháy và hô hấp.!")
                            # else:
                            #     st.write(
                            #         f"📊Xu hướng: Hàm lượng ôxy không có xu hướng rõ ràng, cho thấy nguy cơ than tự cháy ở mức khá an toàn tuy nhiên cần tiếp tục theo dõi.")

                        # # Phân tích thêm (ví dụ: xu hướng)
                        # st.write("🚀Phân tích xu hướng")
                        # # 1. Xác định xu hướng
                        # diff = df[column].diff()
                        # if (diff > 0).sum() > (diff < 0).sum():
                        #     st.write(f"📈Xu hướng: {temp} có xu hướng tăng.")
                        # elif (diff < 0).sum() > (diff > 0).sum():
                        #     st.write(f"📉Xu hướng: {temp} có xu hướng giảm.")
                        # else:
                        #     st.write(f"📊Xu hướng: {temp} không có xu hướng rõ ràng.")

                        # # 2. Phân tích biến động
                        # std = df[column].std()
                        # if std > 0.5:  # Điều chỉnh ngưỡng tùy theo dữ liệu
                        #     st.write(f"🏹Biến động: {temp} có biến động lớn (độ lệch chuẩn: {std:.2f}).")
                        # else:
                        #     st.write(f"⚖️Biến động: {temp} có biến động nhỏ (độ lệch chuẩn: {std:.2f}).")
                        #
                        # # 3. Phân tích các yếu tố khác (ví dụ: thời gian đạt giá trị cao nhất/thấp nhất)
                        # max_time = df[column].idxmax()
                        # min_time = df[column].idxmin()
                        # st.write(f"🕔Thời gian đạt giá trị cao nhất: {max_time}")
                        # st.write(f"🕗Thời gian đạt giá trị thấp nhất: {min_time}")
                        #
                        # # 4. Phân tích các yếu tố đặc biệt (ví dụ: đột biến)
                        # diff_abs = abs(diff)
                        # if (diff_abs > 5).sum() > 0:  # Điều chỉnh ngưỡng tùy theo dữ liệu
                        #     st.write(f"📌Có đột biến trong dữ liệu {temp}.")

                        # ... (thêm các phân tích khác tùy theo yêu cầu) ...
                # Bieu do cot
                for column in selected_columns:
                    if 'NhietDo' in column:
                        y_range = [0, 100]
                        y_title = 'Nhiệt độ (°C)'
                        x_title = 'Thời gian'
                        temp = "nhiệt độ"
                        donvi = "°C"
                        nguong_thap = nguong_nhiet_do_thap
                        nguong_cao = nguong_nhiet_do_cao
                    elif 'Co' in column:
                        y_range = [0, 50]
                        y_title = 'Hàm lượng CO (ppm)'
                        x_title = 'Thời gian'
                        temp = "hàm lượng CO"
                        donvi = "ppm"
                        nguong_thap = nguong_co_thap
                        nguong_cao = nguong_co_cao
                    elif 'Oxy' in column:
                        y_range = [0, 30]
                        y_title = 'Hàm lượng O2 (%)'
                        x_title = 'Thời gian'
                        temp = "hàm lượng O2"
                        donvi = "%"
                        nguong_thap = nguong_o2_thap
                        nguong_cao = nguong_o2_cao

                    st.write(f"<h3 style='color: #34dbac;'>🔯 Biểu đồ phổ {temp}</h3>", unsafe_allow_html=True)

                    # Tạo layout với hai cột
                    col1, col2 = st.columns([2, 1])

                    # Biểu đồ ở cột bên trái
                    with col1:
                        # Thiết lập giới hạn trục hoành
                        if 'NhietDo' in column:
                            x_range = (0, 100)
                            x_title = f'Nhiệt độ ({donvi})'
                        elif 'Co' in column:
                            x_range = (0, 50)  # Cập nhật giới hạn cho CO
                            x_title = f'CO ({donvi})'
                        elif 'Oxy' in column:
                            x_range = (0, 30)
                            x_title = f'O2 ({donvi})'
                        else:
                            x_range = None
                            x_title = column

                        # Vẽ biểu đồ phổ
                        fig_hist = px.histogram(df, x=column, nbins=30, range_x=x_range)

                        # Thêm đường KDE (nếu có thể)
                        if df[column].nunique() > 1:  # Kiểm tra xem dữ liệu có đủ độ biến thiên hay không
                            kde = gaussian_kde(df[column])
                            x_vals = np.linspace(x_range[0], x_range[1], 100)
                            y_vals = kde(x_vals)
                            kde_trace = go.Scatter(x=x_vals, y=y_vals, mode='lines', name='KDE')
                            fig_hist.add_trace(kde_trace)
                        else:
                            st.write("Không thể vẽ đường KDE vì dữ liệu không có đủ độ biến thiên.")

                        fig_hist.update_xaxes(title_text=x_title)
                        fig_hist.update_yaxes(title_text='Tần số')
                        fig_hist.update_layout(showlegend=False)

                        st.plotly_chart(fig_hist)

                    # Giải thích ở cột bên phải
                    with col2:
                        max_val = df[column].max()
                        min_val = df[column].min()
                        mean_val = df[column].mean()
                        st.markdown("📚Giải thích")
                        if 'NhietDo' in column:

                            st.write("📊Biểu đồ phổ nhiệt độ cho thấy phân phối tần suất của các giá trị nhiệt độ được đo.")
                            st.write(
                                "⭕Đường cong KDE (Kernel Density Estimation) mô tả ước lượng mật độ xác suất của dữ liệu, giúp hiểu rõ hơn về hình dạng phân phối.")

                            if max_val > nguong_nhiet_do_cao:
                                st.write(f"⚠️Nhiệt độ vượt quá ngưỡng nguy hiểm {nguong_nhiet_do_cao}°C. Cần kiểm tra ngay lập tức!",)
                            elif max_val > nguong_nhiet_do_thap:
                                st.write(f"❗Nhiệt độ vượt quá ngưỡng cảnh báo {nguong_nhiet_do_thap}°C. Cần theo dõi chặt chẽ.")
                            else:
                                st.write(f"🤩Nhiệt độ nằm trong mức an toàn.")

                            st.write(f"🔴Nhiệt độ cao nhất: {max_val:.1f} {donvi}")
                            st.write(f"🔵Nhiệt độ thấp nhất: {min_val:.1f} {donvi}")
                            st.write(f"⚪Nhiệt độ trung bình: {mean_val:.1f} {donvi}")

                            # Phân tích hình dạng phân phối
                            if df[column].nunique() > 1:  # Kiểm tra xem dữ liệu có đủ độ biến thiên hay không
                                kde = gaussian_kde(df[column])

                                if kde(mean_val) > kde(max_val) and kde(mean_val) > kde(min_val):
                                    st.write("✅Phân phối nhiệt độ có xu hướng tập trung quanh giá trị trung bình.")
                                else:
                                    st.write("💥Phân phối nhiệt độ có thể lệch về phía giá trị cao hoặc thấp.")
                            else:
                                st.write(
                                    "😒Không thể phân tích hình dạng phân phối vì dữ liệu không có đủ độ biến thiên.")
                        elif 'Co' in column:

                            st.write("📊Biểu đồ phổ hàm lượng CO cho thấy phân phối tần suất của các giá trị CO được đo.")
                            st.write("⭕Đường cong KDE mô tả ước lượng mật độ xác suất của dữ liệu.")

                            if max_val > nguong_co_cao:
                                st.write(f"⚠️Hàm lượng CO vượt quá ngưỡng nguy hiểm {nguong_co_cao} ppm. Cần kiểm tra ngay lập tức!")
                            elif max_val > nguong_co_thap:
                                st.write(f"❗Hàm lượng CO vượt quá ngưỡng cảnh báo {nguong_co_thap} ppm. Cần theo dõi chặt chẽ.")
                            else:
                                st.write(f"🤩Hàm lượng CO nằm trong mức an toàn.")

                            st.write(f"🔴Hàm lượng CO cao nhất: {max_val:.1f} {donvi}")
                            st.write(f"🔵Hàm lượng CO thấp nhất: {min_val:.1f} {donvi}")
                            st.write(f"⚪Hàm lượng CO trung bình: {mean_val:.1f} {donvi}")

                            # Phân tích hình dạng phân phối
                            if df[column].nunique() > 1:  # Kiểm tra xem dữ liệu có đủ độ biến thiên hay không
                                kde = gaussian_kde(df[column])

                                if kde(mean_val) > kde(max_val) and kde(mean_val) > kde(min_val):
                                    st.write("✅Phân phối hàm lượng CO có xu hướng tập trung quanh giá trị trung bình.")
                                else:
                                    st.write("💥Phân phối hàm lượng CO có thể lệch về phía giá trị cao hoặc thấp.")
                            else:
                                st.write("😒Không thể phân tích hình dạng phân phối vì dữ liệu không có đủ độ biến thiên.")

                        elif 'Oxy' in column:

                            st.write("📊Biểu đồ phổ hàm lượng O2 cho thấy phân phối tần suất của các giá trị O2 được đo.")
                            st.write("⭕Đường cong KDE mô tả ước lượng mật độ xác suất của dữ liệu.")

                            if min_val < nguong_thap:
                                st.write(
                                    f"⚠️Hàm lượng O2 thấp hơn ngưỡng nguy hiểm ({nguong_thap} {donvi}). Nguy hiểm cho hô hấp! Cần kiểm tra ngay lập tức!")
                            elif max_val < nguong_cao:
                                st.write(
                                    f"❗Hàm lượng O2 thấp hơn ngưỡng nguy hiểm ({nguong_cao} {donvi}). Cần kiểm tra theo dõi.")
                            else:
                                st.write(f"🤩Hàm lượng O2 nằm trong mức an toàn.")

                            st.write(f"🔵Hàm lượng O2 cao nhất: {max_val:.1f} {donvi}")
                            st.write(f"🔴Hàm lượng O2 thấp nhất: {min_val:.1f} {donvi}")
                            st.write(f"⚪Hàm lượng O2 trung bình: {mean_val:.1f} {donvi}")

                            # Phân tích hình dạng phân phối
                            if df[column].nunique() > 1:  # Kiểm tra xem dữ liệu có đủ độ biến thiên hay không
                                kde = gaussian_kde(df[column])

                                if kde(mean_val) > kde(max_val) and kde(mean_val) > kde(min_val):
                                    st.write("✅Phân phối hàm lượng O2 có xu hướng tập trung quanh giá trị trung bình.")
                                else:
                                    st.write("💥Phân phối hàm lượng O2 có thể lệch về phía giá trị cao hoặc thấp.")
                            else:
                                st.write(
                                    "😒Không thể phân tích hình dạng phân phối vì dữ liệu không có đủ độ biến thiên.")
                        # Thêm các giải thích khác dựa trên yêu cầu của bạn
                        # ...

                # Biểu đồ cột (Bar Chart) - Giá trị trung bình mỗi giờ
                # for column in selected_columns:
                #     if 'NhietDo' in column:
                #         y_range = [0, 100]
                #         y_title = 'Nhiệt độ (°C)'
                #         x_title = 'Thời gian'
                #         temp = "nhiệt độ"
                #         donvi = "°C"
                #         nguong_thap = nguong_nhiet_do_thap
                #         nguong_cao = nguong_nhiet_do_cao
                #     elif 'Co' in column:
                #         y_range = [0, 50]
                #         y_title = 'Hàm lượng CO (ppm)'
                #         x_title = 'Thời gian'
                #         temp = "hàm lượng CO"
                #         donvi = "ppm"
                #         nguong_thap = nguong_co_thap
                #         nguong_cao = nguong_co_cao
                #     elif 'Oxy' in column:
                #         y_range = [0, 30]
                #         y_title = 'Hàm lượng O2 (%)'
                #         x_title = 'Thời gian'
                #         temp = "hàm lượng O2"
                #         donvi = "%"
                #         nguong_thap = nguong_o2_thap
                #         nguong_cao = nguong_o2_cao
                #     #st.subheader(f"Biểu đồ cột - Giá trị trung bình của {temp} mỗi giờ")
                #     st.markdown(f"<h3 style='color: #34dbac;'>Biểu đồ cột - Giá trị trung bình của {temp} mỗi giờ</h3>",
                #                 unsafe_allow_html=True)
                #
                #     # Tạo layout với hai cột
                #     col1, col2 = st.columns([2, 1])
                #     with col1:
                #         df_hourly_avg = df.resample('H').mean()
                #         fig_bar_avg = px.bar(df_hourly_avg, x=df_hourly_avg.index, y=selected_columns)
                #         fig_bar_avg.update_xaxes(title_text='Thời gian')
                #         fig_bar_avg.update_yaxes(title_text=f'Giá trị trung bình của {donvi}')
                #         fig_bar_avg.update_layout(showlegend=False)  # Ẩn ghi chú
                #         st.plotly_chart(fig_bar_avg)
                #         # Giải thích ở cột bên phải
                #     with col2:
                #         # Lấy giá trị trung bình lớn nhất và nhỏ nhất
                #         max_val = df_hourly_avg[column].max()
                #         min_val = df_hourly_avg[column].min()
                #         st.markdown("### Giải thích")
                #         # Thêm logic If-Then để tạo giải thích
                #         if 'NhietDo' in column:
                #
                #             if max_val > nguong_nhiet_do_cao:
                #                 st.write(
                #                     f"- Nhiệt độ vượt quá ngưỡng nguy hiểm {nguong_nhiet_do_cao}°C. Cần kiểm tra ngay lập tức!")
                #             elif max_val > nguong_nhiet_do_thap:
                #                 st.write(
                #                     f"- Nhiệt độ vượt quá ngưỡng cảnh báo {nguong_nhiet_do_thap}°C. Cần theo dõi chặt chẽ.")
                #             else:
                #                 st.write(f"- Nhiệt độ nằm trong mức an toàn.")
                #             st.write(f"- Nhiệt độ cao nhất: {max_val:.1f} {donvi}.")
                #             st.write(f"- Nhiệt độ thấp nhất: {min_val:.1f} {donvi}.")
                #
                #         elif 'Co' in column:
                #
                #             if max_val > nguong_co_cao:
                #                 st.write(
                #                     f"- Hàm lượng CO vượt quá ngưỡng nguy hiểm {nguong_co_cao} ppm. Cần kiểm tra ngay lập tức!")
                #             elif max_val > nguong_co_thap:
                #                 st.write(
                #                     f"- Hàm lượng CO vượt quá ngưỡng cảnh báo {nguong_co_thap} ppm. Cần theo dõi chặt chẽ.")
                #             else:
                #                 st.write(f"- Hàm lượng CO nằm trong mức an toàn.")
                #
                #             st.write(f"- Hàm lượng CO cao nhất: {max_val:.1f} {donvi}.")
                #             st.write(f"- Hàm lượng CO thấp nhất: {min_val:.1f} {donvi}.")
                #
                #         elif 'Oxy' in column:
                #
                #             if min_val < nguong_thap:
                #                 st.write(
                #                     f"- Hàm lượng O2 thấp hơn ngưỡng nguy hiểm ({nguong_thap} {donvi}). Nguy hiểm cho hô hấp! Cần kiểm tra ngay lập tức!")
                #             elif max_val < nguong_cao:
                #                 st.write(
                #                     f"- Hàm lượng O2 thấp hơn ngưỡng nguy hiểm ({nguong_cao} {donvi}). Cần kiểm tra theo dõi.")
                #             else:
                #                 st.write(f"- Hàm lượng O2 nằm trong mức an toàn.")
                #
                #             st.write(f"- Hàm lượng O2 cao nhất: {max_val:.1f} {donvi}.")
                #             st.write(f"- Hàm lượng O2 thấp nhất: {min_val:.1f} {donvi}.")
                #
                #         # Thêm các giải thích khác dựa trên yêu cầu của bạn
                #         # ...

                for column in selected_columns:
                    if 'NhietDo' in column:
                        y_range = [0, 100]
                        y_title = 'Nhiệt độ (°C)'
                        x_title = 'Thời gian'
                        temp = "nhiệt độ"
                        donvi = "°C"
                        nguong_thap = nguong_nhiet_do_thap
                        nguong_cao = nguong_nhiet_do_cao
                    elif 'Co' in column:
                        y_range = [0, 50]
                        y_title = 'Hàm lượng CO (ppm)'
                        x_title = 'Thời gian'
                        temp = "hàm lượng CO"
                        donvi = "ppm"
                        nguong_thap = nguong_co_thap
                        nguong_cao = nguong_co_cao
                    elif 'Oxy' in column:
                        y_range = [0, 30]
                        y_title = 'Hàm lượng O2 (%)'
                        x_title = 'Thời gian'
                        temp = "hàm lượng O2"
                        donvi = "%"
                        nguong_thap = nguong_o2_thap
                        nguong_cao = nguong_o2_cao

                    st.markdown(f"<h3 style='color: #34dbac;'>✴️ Biểu đồ đường - Giá trị trung bình của {temp} mỗi giờ</h3>",
                                unsafe_allow_html=True)

                    # Tạo layout với hai cột
                    col1, col2 = st.columns([2, 1])

                    # Biểu đồ ở cột bên trái
                    with col1:
                        df_hourly_avg = df.resample('h').mean()

                        fig_line_avg = px.line(df_hourly_avg, x=df_hourly_avg.index, y=column)  # Chỉ vẽ một cột
                        fig_line_avg.update_xaxes(title_text='Thời gian')
                        fig_line_avg.update_yaxes(title_text=f'Giá trị trung bình của {temp} {donvi}')
                        fig_line_avg.update_layout(showlegend=False)
                        st.plotly_chart(fig_line_avg)

                    # Giải thích ở cột bên phải
                    with col2:
                        # Lấy giá trị trung bình lớn nhất và nhỏ nhất
                        max_val = df_hourly_avg[column].max()
                        min_val = df_hourly_avg[column].min()
                        mean_val = df_hourly_avg[column].mean()

                        st.markdown("📚Giải thích")
                        # Thêm logic If-Then để tạo giải thích
                        if 'NhietDo' in column:

                            if max_val > nguong_nhiet_do_cao:
                                st.write(
                                    f"⚠️Nhiệt độ trung bình vượt quá ngưỡng nguy hiểm {nguong_nhiet_do_cao}°C. Cần kiểm tra ngay lập tức!")
                            elif max_val > nguong_nhiet_do_thap:
                                st.write(
                                    f"❗Nhiệt độ trung bình vượt quá ngưỡng cảnh báo {nguong_nhiet_do_thap}°C. Cần theo dõi chặt chẽ.")
                            else:
                                st.write(f"🤩Nhiệt độ trung bình nằm trong mức an toàn.")

                        elif 'Co' in column:

                            if max_val > nguong_co_cao:
                                st.write(
                                    f"⚠️Hàm lượng CO trung bình vượt quá ngưỡng nguy hiểm {nguong_co_cao} ppm. Cần kiểm tra ngay lập tức!")
                            elif max_val > nguong_co_thap:
                                st.write(
                                    f"❗Hàm lượng CO trung bình vượt quá ngưỡng cảnh báo {nguong_co_thap} ppm. Cần theo dõi chặt chẽ.")
                            else:
                                st.write(f"🤩Hàm lượng CO trung bình nằm trong mức an toàn.")

                        elif 'Oxy' in column:

                            if min_val < nguong_thap:
                                st.write(
                                    f"⚠️Hàm lượng O2 trung bình thấp hơn ngưỡng nguy hiểm ({nguong_thap} {donvi}). Nguy hiểm cho hô hấp! Cần kiểm tra ngay lập tức!")
                            elif max_val < nguong_cao:
                                st.write(
                                    f"❗Hàm lượng O2 trung bình thấp hơn ngưỡng nguy hiểm ({nguong_cao} {donvi}). Cần kiểm tra theo dõi.")
                            else:
                                st.write(f"🤩Hàm lượng O2 trung bình nằm trong mức an toàn.")

                        st.write(f"🔴Giá trị trung bình cao nhất: {max_val:.2f} {donvi}.")
                        st.write(f"🔵Giá trị trung bình thấp nhất: {min_val:.2f} {donvi}.")
                        st.write(f"⚪Giá trị trung bình: {mean_val:.2f} {donvi}.")

                        # Phân tích thêm
                        st.markdown("🚀Phân tích thêm")

                        # 1. Xác định xu hướng
                        diff = df_hourly_avg[column].diff()
                        if (diff > 0).sum() > (diff < 0).sum():
                            st.write(f"📈Xu hướng: {temp} trung bình có xu hướng tăng.")
                        elif (diff < 0).sum() > (diff > 0).sum():
                            st.write(f"📉Xu hướng: {temp} trung bình có xu hướng giảm.")
                        else:
                            st.write(f"⚖️Xu hướng: {temp} trung bình không có xu hướng rõ ràng.")

                        # 2. Phân tích biến động
                        std = df_hourly_avg[column].std()
                        if std > 0.5:  # Điều chỉnh ngưỡng tùy theo dữ liệu
                            st.write(f"🏹Biến động: {temp} trung bình có biến động lớn (độ lệch chuẩn: {std:.2f}).")
                        else:
                            st.write(f"🔰Biến động: {temp} trung bình có biến động nhỏ (độ lệch chuẩn: {std:.2f}).")

                        # 3. Phân tích các yếu tố khác (ví dụ: thời gian đạt giá trị cao nhất/thấp nhất)
                        max_time = df_hourly_avg[column].idxmax()
                        min_time = df_hourly_avg[column].idxmin()
                        st.write(f"🕢Thời gian đạt giá trị trung bình cao nhất: {max_time}")
                        st.write(f"🕤Thời gian đạt giá trị trung bình thấp nhất: {min_time}")

                        # 4. Phân tích các yếu tố đặc biệt (ví dụ: đột biến)
                        diff_abs = abs(diff)
                        if (diff_abs > 5).sum() > 0:  # Điều chỉnh ngưỡng tùy theo dữ liệu
                            st.write(f"📈Có đột biến trong dữ liệu {temp}.")
                            # ... (thêm phân tích chi tiết về đột biến) ...

                        # Thêm các giải thích khác dựa trên yêu cầu của bạn
                        # ...

                # Biểu đồ cột (Bar Chart) - Giá trị lớn nhất mỗi giờ
                # for column in selected_columns:
                #     if 'NhietDo' in column:
                #         y_range = [0, 100]
                #         y_title = 'Nhiệt độ (°C)'
                #         x_title = 'Thời gian'
                #         temp = "nhiệt độ"
                #         donvi = "°C"
                #         nguong_thap = nguong_nhiet_do_thap
                #         nguong_cao = nguong_nhiet_do_cao
                #     elif 'Co' in column:
                #         y_range = [0, 50]
                #         y_title = 'Hàm lượng CO (ppm)'
                #         x_title = 'Thời gian'
                #         temp = "hàm lượng CO"
                #         donvi = "ppm"
                #         nguong_thap = nguong_co_thap
                #         nguong_cao = nguong_co_cao
                #     elif 'Oxy' in column:
                #         y_range = [0, 30]
                #         y_title = 'Hàm lượng O2 (%)'
                #         x_title = 'Thời gian'
                #         temp = "hàm lượng O2"
                #         donvi = "%"
                #         nguong_thap = nguong_o2_thap
                #         nguong_cao = nguong_o2_cao
                #     # Tạo layout với hai cột
                #     col1, col2 = st.columns([2, 1])
                #
                #     # Cột 1: Hiển thị biểu đồ
                #     with col1:
                #         #st.subheader(f"Biểu đồ cột - Giá trị lớn nhất của {temp} mỗi giờ")
                #         st.markdown(f"<h3 style='color: #34dbac;'>Biểu đồ cột - Giá trị lớn nhất của {temp} mỗi giờ</h3>",
                #                     unsafe_allow_html=True)
                #         df_hourly_max = df.resample('H').max()
                #         fig_bar_max = px.bar(df_hourly_max, x=df_hourly_max.index, y=selected_columns)
                #         fig_bar_max.update_xaxes(title_text='Thời gian')
                #         fig_bar_max.update_yaxes(title_text=f'Giá trị lớn nhất của {donvi}')
                #         fig_bar_max.update_layout(showlegend=False)  # Ẩn ghi chú
                #         st.plotly_chart(fig_bar_max)
                #     # Cột 2: Giải thích ý nghĩa của biểu đồ và kiểm tra ngưỡng
                #     # Lấy giá trị lớn nhất của cột hiện tại
                #     max_value = df_hourly_max[column].max()
                #     with col2:
                #         st.markdown("### Giải thích")
                #         if 'NhietDo' in column:
                #             st.write(f"**Giá trị lớn nhất của {temp}: {max_value} {donvi}**")
                #             if max_value < nguong_thap:
                #                 st.write(
                #                     f"- Nhiệt độ hiện tại **an toàn**, dưới ngưỡng cảnh báo thấp ({nguong_thap} °C).")
                #             elif nguong_thap <= max_value < nguong_cao:
                #                 st.write(f"- Nhiệt độ đang **tiếp cận ngưỡng nguy hiểm**, cần theo dõi chặt chẽ.")
                #             else:
                #                 st.write(
                #                     f"- Nhiệt độ đã **vượt ngưỡng cảnh báo cao** ({nguong_cao} °C), cần có biện pháp xử lý ngay.")
                #             st.write("""
                #                         **Tại sao cần theo dõi nhiệt độ?**
                #                         - Nhiệt độ cao có thể là dấu hiệu của quá trình oxy hóa tự nhiên, dẫn đến tự cháy trong than.
                #                         - Theo dõi nhiệt độ giúp phát hiện sớm các điểm nóng trong vỉa than, từ đó có biện pháp phòng ngừa kịp thời.
                #                         """)
                #         elif 'Co' in column:
                #             st.write(f"**Giá trị lớn nhất của {temp}: {max_value} {donvi}**")
                #             if max_value < nguong_thap:
                #                 st.write(
                #                     f"- Hàm lượng CO hiện tại **an toàn**, dưới ngưỡng cảnh báo thấp ({nguong_thap} ppm).")
                #             elif nguong_thap <= max_value < nguong_cao:
                #                 st.write(f"- Hàm lượng CO đang **tiếp cận ngưỡng nguy hiểm**, cần theo dõi chặt chẽ.")
                #             else:
                #                 st.write(
                #                     f"- Hàm lượng CO đã **vượt ngưỡng cảnh báo cao** ({nguong_cao} ppm), cần có biện pháp xử lý ngay.")
                #             st.write("""
                #                         **Tại sao cần theo dõi hàm lượng CO?**
                #                         - CO là khí độc nguy hiểm, có thể gây ngộ độc cấp tính cho công nhân.
                #                         - Hàm lượng CO tăng cao là dấu hiệu của quá trình tự cháy của than hoặc do bắn mìn.
                #                         """)
                #         elif 'Oxy' in column:
                #             st.write(f"**Giá trị lớn nhất của {temp}: {max_value} {donvi}**")
                #             if min_val < nguong_thap:
                #                 st.write(
                #                     f"- Hàm lượng O2 thấp hơn ngưỡng nguy hiểm ({nguong_thap} {donvi}). Nguy hiểm cho hô hấp! Cần kiểm tra ngay lập tức!")
                #             elif max_val < nguong_cao:
                #                 st.write(
                #                     f"- Hàm lượng O2 thấp hơn ngưỡng nguy hiểm ({nguong_cao} {donvi}). Cần kiểm tra theo dõi.")
                #             else:
                #                 st.write(f"- Hàm lượng O2 nằm trong mức an toàn.")
                #             st.write("""
                #                         **Tại sao cần theo dõi hàm lượng O2?**
                #                         - Oxy là yếu tố cần thiết cho quá trình cháy và hô hấp.
                #                         - Hàm lượng O2 thấp có thể gây ngạt thở.
                #                         """)
                # Biểu đồ đường - Giá trị lớn nhất mỗi giờ
                for column in selected_columns:
                    if 'NhietDo' in column:
                        y_range = [0, 100]
                        y_title = 'Nhiệt độ (°C)'
                        x_title = 'Thời gian'
                        temp = "nhiệt độ"
                        donvi = "°C"
                        nguong_thap = nguong_nhiet_do_thap
                        nguong_cao = nguong_nhiet_do_cao
                    elif 'Co' in column:
                        y_range = [0, 50]
                        y_title = 'Hàm lượng CO (ppm)'
                        x_title = 'Thời gian'
                        temp = "hàm lượng CO"
                        donvi = "ppm"
                        nguong_thap = nguong_co_thap
                        nguong_cao = nguong_co_cao
                    elif 'Oxy' in column:
                        y_range = [0, 30]
                        y_title = 'Hàm lượng O2 (%)'
                        x_title = 'Thời gian'
                        temp = "hàm lượng O2"
                        donvi = "%"
                        nguong_thap = nguong_o2_thap
                        nguong_cao = nguong_o2_cao

                    df_hourly_max = df.resample('h').max()
                    # Lấy giá trị lớn nhất của cột hiện tại
                    max_value = df_hourly_max[column].max()

                    # Tạo layout với hai cột
                    col1, col2 = st.columns([2, 1])

                    # Cột 1: Hiển thị biểu đồ
                    with col1:
                        st.markdown(f"<h3 style='color: #34dbac;'>💫 Biểu đồ đường - Giá trị lớn nhất của {temp} mỗi giờ</h3>",
                                    unsafe_allow_html=True)
                        fig_line_max = px.line(df_hourly_max, x=df_hourly_max.index, y=column)
                        fig_line_max.update_xaxes(title_text='Thời gian')
                        fig_line_max.update_yaxes(title_text=f'Giá trị lớn nhất của {temp} {donvi}')
                        fig_line_max.update_layout(showlegend=False)  # Ẩn ghi chú
                        st.plotly_chart(fig_line_max)
                    # Cột 2: Giải thích ý nghĩa của biểu đồ và kiểm tra ngưỡng
                    with col2:
                        st.markdown("📚Giải thích")
                        if 'NhietDo' in column:
                            st.write(f"**📌Giá trị lớn nhất của {temp}: {max_value} {donvi}**")
                            if max_value < nguong_thap:
                                st.write(f"🤩Nhiệt độ lớn nhất hiện tại **an toàn**, dưới ngưỡng cảnh báo thấp ({nguong_thap} °C).")
                            elif nguong_thap <= max_value < nguong_cao:
                                st.write(f"⚠️Nhiệt độ lớn nhất đang **tiếp cận ngưỡng nguy hiểm**, cần theo dõi chặt chẽ.")
                            else:
                                st.write(
                                    f"❗Nhiệt độ lớn nhất đã **vượt ngưỡng cảnh báo cao** ({nguong_cao} °C), cần có biện pháp xử lý ngay.")
                            st.write("""
                            **❓Tại sao cần theo dõi nhiệt độ?**  
                            👉Nhiệt độ cao có thể là dấu hiệu của quá trình oxy hóa tự nhiên, dẫn đến tự cháy trong than.  
                            👉Theo dõi nhiệt độ giúp phát hiện sớm các điểm nóng trong vỉa than, từ đó có biện pháp phòng ngừa kịp thời.
                            """)
                        elif 'Co' in column:
                            st.write(f"**Giá trị lớn nhất của {temp}: {max_value} {donvi}**")
                            if max_value < nguong_thap:
                                st.write(
                                    f"🤩Hàm lượng CO lớn nhất hiện tại **an toàn**, dưới ngưỡng cảnh báo thấp ({nguong_thap} ppm).")
                            elif nguong_thap <= max_value < nguong_cao:
                                st.write(f"❗Hàm lượng CO lớn nhất đang **tiếp cận ngưỡng cao**, cần theo dõi chặt chẽ.")
                            else:
                                st.write(
                                    f"⚠️Hàm lượng CO lớn nhất đã **vượt ngưỡng cảnh báo cao** ({nguong_cao} ppm), cần có biện pháp xử lý ngay.")
                            st.write("""
                            **❓Tại sao cần theo dõi hàm lượng CO?**  
                            👉CO là khí độc nguy hiểm, có thể gây ngộ độc cấp tính cho công nhân.  
                            👉Hàm lượng CO tăng liên tục là dấu hiệu của quá trình tự cháy của than. Tăng đột biến và giảm là do bắn mìn.
                            """)
                        elif 'Oxy' in column:
                            st.write(f"**Giá trị lớn nhất của {temp}: {max_value} {donvi}**")
                            # if min_val < nguong_thap:
                            #     st.write(
                            #         f"❗Hàm lượng O2 lớn nhất thấp hơn ngưỡng nguy hiểm ({nguong_thap} {donvi}). Nguy hiểm cho hô hấp! Cần kiểm tra ngay lập tức!")
                            # elif max_val < nguong_cao:
                            #     st.write(
                            #         f"⚠️Hàm lượng O2 lớn nhất thấp hơn ngưỡng nguy hiểm ({nguong_cao} {donvi}). Cần kiểm tra theo dõi.")
                            # else:
                            #     st.write(f"🤩Hàm lượng O2 lớn nhất nằm trong mức an toàn.")
                            st.write("""
                            **❓Tại sao cần theo dõi hàm lượng O2?**  
                            👉Oxy là yếu tố cần thiết cho quá trình cháy và hô hấp.  
                            👉Hàm lượng O2 thấp có thể gây ngạt thở.
                            """)
            else:
                st.warning("Không có dữ liệu phù hợp với điều kiện truy vấn. Bạn xem lại đã chọn thời gian đúng chưa, chú ý thời điểm đầu phải trước thời điểm sau nhé!")

# Nút nhấn để vẽ bản đồ tương quan cho từng khu vực
if st.sidebar.button("〽️Vẽ biểu đồ tương quan từng khu"):
    # Kiểm tra xem người dùng đã chọn thời gian và khu vực hay chưa
    if not kiemtra_thoigian or not selected_khu_vuc:
        st.warning("🤭Vui lòng chọn đầy đủ thời gian và khu vực. Thời gian kết thúc phải lớn hơn thời gian bắt đầu!")
    else:
        with st.spinner('⌛Đang tải dữ liệu...'):
            df = get_data(start_datetime, end_datetime, [col for khu in selected_khu_vuc for col in khu_vuc[khu]])

            if not df.empty:
                df.fillna(df.mean(), inplace=True)  # Thay thế giá trị NULL bằng trung bình
                df['date_time'] = pd.to_datetime(df['date_time'])  # Chuyển đổi cột thời gian
                df.set_index('date_time', inplace=True)

                # Vẽ bản đồ nhiệt cho từng khu vực
                for khu_name, columns in khu_vuc.items():
                    if khu_name in selected_khu_vuc:
                        if khu_name == "Tủ 1 khu 1":
                            temp = "Tủ giám sát phòng nổ 1 khu vực giám sát 1"
                        elif khu_name == "Tủ 1 khu 2":
                            temp = "Tủ giám sát phòng nổ 1 khu vực giám sát 2"
                        elif khu_name == "Tủ 2 khu 1":
                            temp = "Tủ giám sát phòng nổ 2 khu vực giám sát 1"
                        elif khu_name == "Tủ 2 khu 2":
                            temp = "Tủ giám sát phòng nổ 2 khu vực giám sát 2"

                        st.markdown(f"<h3 style='color: #34dbac;'>❇️ Biểu đồ tương quan 2D - {temp}</h3>", unsafe_allow_html=True)

                        # Chia layout thành 2 cột
                        col1, col2 = st.columns([2, 1])  # Cột trái nhỏ hơn cột phải

                        with col1:
                            # Hiển thị bản đồ nhiệt
                            corr_matrix = df[columns].corr()
                            fig, ax = plt.subplots(figsize=(5, 4))
                            sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", square=True, linewidths=0.5, ax=ax)
                            ax.set_xlabel('Thông số')
                            ax.set_ylabel('Thông số')
                            st.pyplot(fig)

                        with col2:
                            # Hiển thị phần giải thích
                            analysis_text = f"""
                            **📚Phân tích bản đồ tương quan - {temp}:**
                            - **Mô tả:** Bản đồ nhiệt này thể hiện mức độ tương quan giữa các thông số đo lường trong khu vực {temp}.
                            - **Giá trị tương quan:** Giá trị nằm trong khoảng từ -1 đến 1, trong đó:
                            - 🔵 Giá trị gần 1: Có tương quan dương mạnh.
                            - 🔴 Giá trị gần -1: Có tương quan âm mạnh.
                            - ⚪ Giá trị gần 0: Không có tương quan đáng kể.
                            """
                            st.markdown(analysis_text, unsafe_allow_html=True)

                            # Phân tích cụ thể cho từng cặp biến
                            for i, col1 in enumerate(columns):
                                for j, col2 in enumerate(columns):
                                    if i < j:
                                        corr_value = corr_matrix.loc[col1, col2]
                                        analysis_pair = ""  # Khởi tạo biến analysis_pair
                                        if corr_value >= 0.8:
                                            analysis_pair = f"""
                                            - **Tương quan giữa {col1} và {col2}:** {corr_value:.2f}
                                            - **Ý nghĩa:** Có mối quan hệ chặt chẽ giữa hai thông số, sự thay đổi của một thông số sẽ ảnh hưởng mạnh đến thông số còn lại.
                                            - 🔴 **Cảnh báo:** Cần theo dõi sát vì bất kỳ biến động nào cũng có thể gây ra sự thay đổi đáng kể.
                                            """
                                        elif 0.5 <= corr_value < 0.8:
                                            analysis_pair = f"""
                                            - **Tương quan giữa {col1} và {col2}:** {corr_value:.2f}
                                            - **Ý nghĩa:** Hai thông số có tương quan dương khá rõ ràng, có thể được khai thác để dự báo hoặc điều khiển.
                                            - ✅ **Ứng dụng:** Có thể sử dụng một thông số để dự đoán thông số còn lại trong hệ thống giám sát.
                                            """
                                        elif 0.2 <= corr_value < 0.5:
                                            analysis_pair = f"""
                                            - **Tương quan giữa {col1} và {col2}:** {corr_value:.2f}
                                            - **Ý nghĩa:** Có xu hướng tương quan dương nhưng không quá mạnh, có thể bị ảnh hưởng bởi nhiều yếu tố khác.
                                            - 🔍 **Lưu ý:** Cần kiểm tra thêm các biến trung gian khác để hiểu rõ hơn về mối quan hệ này.
                                            """
                                        elif -0.2 <= corr_value <= 0.2:
                                            if ("NhietDo" in col1 and "Co" in col2) or ("NhietDo" in col2 and "Co" in col1):
                                                analysis_pair = f"""
                                                - **Tương quan giữa {col1} và {col2}:** {corr_value:.2f}
                                                - **Ý nghĩa:** Không có mối tương quan rõ ràng giữa nhiệt độ trong vỉa than và hàm lượng khí CO tại vị trí đo.
                                                - 📌 **Giải thích:**
                                                - Cảm biến đo CO có thể bị ảnh hưởng bởi luồng gió mỏ hoặc khoảng cách đến nguồn phát thải.
                                                - Khi vỉa than nóng lên, CO có thể sinh ra, nhưng thông gió có thể làm pha loãng hoặc vận chuyển khí CO đi nơi khác.
                                                - Cần phân tích chuỗi thời gian để xác định độ trễ giữa nhiệt độ và sự hình thành CO.
                                                """
                                            elif ("NhietDo" in col1 and "Oxy" in col2) or (
                                                    "NhietDo" in col2 and "Oxy" in col1):
                                                analysis_pair = f"""
                                                - **Tương quan giữa {col1} và {col2}:** {corr_value:.2f}
                                                - **Ý nghĩa:** Mối quan hệ giữa nhiệt độ và O₂ có thể bị ảnh hưởng bởi quá trình oxy hóa và hệ thống thông gió.
                                                - 📌 **Giải thích:**
                                                - Khi than bị oxy hóa, oxy bị tiêu thụ, nhưng nếu thông gió mạnh, nồng độ O₂ có thể không giảm đáng kể.
                                                - Dữ liệu hiện tại chưa cho thấy rõ ràng quá trình tiêu thụ O₂ trong quá trình cháy âm ỉ.
                                                - Cần kiểm tra điều kiện dòng khí để có đánh giá chính xác hơn.
                                                """
                                            elif ("Co" in col1 and "Oxy" in col2) or ("Co" in col2 and "Oxy" in col1):
                                                analysis_pair = f"""
                                                - **Tương quan giữa {col1} và {col2}:** {corr_value:.2f}
                                                - **Ý nghĩa:** Hàm lượng CO và O₂ không có mối quan hệ nghịch biến rõ ràng do ảnh hưởng của thông gió.
                                                - 📌 **Giải thích:**
                                                - Nếu CO tăng do cháy âm ỉ, O₂ có thể bị tiêu thụ, nhưng thông gió có thể làm loãng cả hai khí này.
                                                - **Một nguyên nhân khác:** Khi bắn mìn để khai thác than, CO có thể tăng mạnh do quá trình đốt cháy thuốc nổ, đồng thời O₂ giảm do phản ứng hóa học.
                                                - **Quan trọng:** Trong trường hợp này, nhiệt độ vỉa than không thay đổi đáng kể vì sự gia tăng CO là do yếu tố bên ngoài, không phải do quá trình oxy hóa than.
                                                - Cần phân tích theo thời gian để xem xét sự thay đổi đồng thời của ba thông số này.
                                                """
                                            else:
                                                analysis_pair = f"""
                                                - **Tương quan giữa {col1} và {col2}:** {corr_value:.2f}
                                                - **Ý nghĩa:** Không có mối tương quan đáng kể giữa hai thông số.
                                                - 📌 **Giải thích:** Hai thông số này có thể không liên quan hoặc có quan hệ phi tuyến tính.
                                                """
                                        elif -0.5 < corr_value < -0.2:
                                            analysis_pair = f"""
                                            - **Tương quan giữa {col1} và {col2}:** {corr_value:.2f}
                                            - **Ý nghĩa:** Có xu hướng tương quan âm nhẹ đến trung bình, nhưng không quá rõ ràng.
                                            - 🔍 **Lưu ý:** Mối quan hệ này có thể bị ảnh hưởng bởi nhiều yếu tố khác.
                                            """
                                        elif -0.8 < corr_value <= -0.5:
                                            analysis_pair = f"""
                                            - **Tương quan giữa {col1} và {col2}:** {corr_value:.2f}
                                            - **Ý nghĩa:** Hai thông số có mối quan hệ nghịch biến khá rõ ràng.
                                            - ❗ **Cảnh báo:** Nếu một thông số tăng, thông số còn lại có thể giảm mạnh, cần theo dõi cẩn thận.
                                            """
                                        elif corr_value <= -0.8:
                                            analysis_pair = f"""
                                            - **Tương quan giữa {col1} và {col2}:** {corr_value:.2f}
                                            - **Ý nghĩa:** Khi một thông số tăng, thông số kia có xu hướng giảm mạnh.
                                            - 🔴 **Lưu ý:** Cần kiểm tra nguyên nhân nếu tương quan này ảnh hưởng đến hoạt động của hệ thống.
                                            """

                                        st.markdown(analysis_pair, unsafe_allow_html=True)

                        # Vẽ biểu đồ 3D cho từng khu vực  Bản đồ tương quan 2D
                        if len(columns) == 3:
                            col1, col2, col3 = columns

                            st.markdown(f"<h3 style='color: #34dbac;'>💎 Biểu đồ 3D - {temp}</h3>",
                                        unsafe_allow_html=True)
                            # Chia layout thành 2 cột
                            col_left, col_right = st.columns([2, 1])  # Cột trái nhỏ hơn cột phải

                            with col_left:
                                # Hiển thị biểu đồ 3D
                                fig_3d = px.scatter_3d(df, x=col1, y=col2, z=col3,
                                                       labels={col1: col1, col2: col2, col3: col3},
                                                       width=1000, height=700)  # Tăng kích thước biểu đồ 3D
                                fig_3d.update_traces(marker=dict(size=5, opacity=0.7))
                                st.plotly_chart(fig_3d)

                                with col_right:
                                    # Phân tích biểu đồ 3D
                                    analysis_3d = f"""
                                                **📚Phân tích biểu đồ 3D giữa {col1}, {col2} và {col3}:**
                                                - **Ý nghĩa:** Điểm trên biểu đồ 3D đại diện cho một thời điểm cụ thể với các giá trị của ba thông số tương ứng.
                                                - **📊Phân tích cụ thể:**
                                                """
                                    st.markdown(analysis_3d, unsafe_allow_html=True)

                                    # Phân tích cụ thể cho từng nhóm điểm
                                    # Ngưỡng cho O2
                                    low_oxy_1 = df[col3] < nguong_o2_thap
                                    low_oxy_2 = (df[col3] >= nguong_o2_thap) & (df[col3] < nguong_o2_cao)
                                    high_oxy = df[col3] >= nguong_o2_cao

                                    # Ngưỡng cho CO
                                    high_co_1 = df[col2] > nguong_co_cao
                                    high_co_2 = (df[col2] > nguong_co_thap) & (df[col2] <= nguong_co_cao)
                                    low_co = df[col2] <= nguong_co_thap

                                    # Ngưỡng cho Nhiệt độ
                                    high_temp_1 = df[col1] > nguong_nhiet_do_cao
                                    high_temp_2 = (df[col1] > nguong_nhiet_do_thap) & (df[col1] <= nguong_nhiet_do_cao)
                                    low_temp = df[col1] <= nguong_nhiet_do_thap

                                    # Nhóm điểm có nhiệt độ cao, hàm lượng CO cao, hàm lượng O2 thấp
                                    if (high_temp_1 | high_temp_2).any() and (
                                            high_co_1 | high_co_2).any() and low_oxy_1.any():
                                        analysis_group = f"""
                                                    - **⚠️Nhóm điểm có {col1} cao, {col2} cao và {col3} thấp:**
                                                    - **Ý nghĩa:** Khi nhiệt độ và hàm lượng CO tăng, hàm lượng O₂ thường giảm.
                                                    - **Giải thích:** Quá trình oxy hóa than mạnh có thể tiêu thụ nhiều O₂, dẫn đến sự giảm hàm lượng O₂.
                                                    - **Cảnh báo:** Cần kiểm tra để đảm bảo an toàn.
                                                    """
                                        st.markdown(analysis_group, unsafe_allow_html=True)
                                    else:
                                        analysis_group = f"""
                                                    - **⭐Không tìm thấy nhóm điểm có {col1} cao, {col2} cao và {col3} thấp.**
                                                    - **Giải thích:** Có thể do dữ liệu không đủ hoặc các yếu tố khác ảnh hưởng đến sự tương quan.
                                                    - **Lưu ý:** Cần thu thập thêm dữ liệu.
                                                    """
                                        st.markdown(analysis_group, unsafe_allow_html=True)

                                    # Nhóm điểm có nhiệt độ thấp, hàm lượng CO thấp, hàm lượng O2 cao
                                    if low_temp.any() and low_co.any() and high_oxy.any():
                                        analysis_group = f"""
                                                    - **🤩Nhóm điểm có {col1} thấp, {col2} thấp và {col3} cao:**
                                                    - **Ý nghĩa:** Khi nhiệt độ và hàm lượng CO thấp, hàm lượng O₂ cao.
                                                    - **Giải thích:** Quá trình oxy hóa than yếu hoặc không diễn ra, dẫn đến hàm lượng O₂ cao.
                                                    """
                                        st.markdown(analysis_group, unsafe_allow_html=True)
                                    else:
                                        analysis_group = f"""
                                                    - **😄Không tìm thấy nhóm điểm có {col1} thấp, {col2} thấp và {col3} cao.**
                                                    - **Giải thích:** Có thể do dữ liệu không đủ hoặc các yếu tố khác ảnh hưởng đến sự tương quan.
                                                    - **Lưu ý:** Cần thu thập thêm dữ liệu.
                                                    """
                                        st.markdown(analysis_group, unsafe_allow_html=True)

                                    # Phân tích thêm các nhóm điểm khác nếu cần
                                    # Ví dụ: Nhóm điểm có nhiệt độ cao, hàm lượng CO thấp, hàm lượng O2 thấp
                                    if (high_temp_1 | high_temp_2).any() and low_co.any() and low_oxy_1.any():
                                        analysis_group = f"""
                                                    - **🪔Nhóm điểm có {col1} cao, {col2} thấp và {col3} thấp:**
                                                    - **Ý nghĩa:** Khi nhiệt độ cao nhưng hàm lượng CO thấp, hàm lượng O₂ thường giảm.
                                                    - **Giải thích:** Có thể do oxy hóa than.
                                                     - **Cảnh báo:** Cần kiểm tra nguyên nhân gây ra sự gia tăng nhiệt độ.
                                                    """
                                        st.markdown(analysis_group, unsafe_allow_html=True)
                                    else:
                                        analysis_group = f"""
                                                    - **😍Không tìm thấy nhóm điểm có {col1} cao, {col2} thấp và {col3} thấp.**
                                                    - **Giải thích:** Có thể do dữ liệu không đủ hoặc các yếu tố khác ảnh hưởng đến sự tương quan.
                                                    - **Lưu ý:** Cần thu thập thêm dữ liệu.
                                                    """
                                        st.markdown(analysis_group, unsafe_allow_html=True)

                                    # Nhóm điểm có nhiệt độ thấp, hàm lượng CO cao, hàm lượng O2 thấp
                                    if low_temp.any() and (high_co_1 | high_co_2).any() and low_oxy_1.any():
                                        analysis_group = f"""
                                                    - **🧨Nhóm điểm có {col1} thấp, {col2} cao và {col3} thấp:**
                                                    - **Ý nghĩa:** Khi nhiệt độ thấp nhưng hàm lượng CO cao, hàm lượng O₂ thường giảm.
                                                    - **Giải thích:** Có thể do việc bắn mìn gây ra sự gia tăng hàm lượng CO mà không liên quan đến than tự cháy.
                                                    - **Cảnh báo:** Cần kiểm tra nguyên nhân gây ra sự gia tăng hàm lượng CO.
                                                    """
                                        st.markdown(analysis_group, unsafe_allow_html=True)
                                    else:
                                        analysis_group = f"""
                                                    - **😧Không tìm thấy nhóm điểm có {col1} thấp, {col2} cao và {col3} thấp.**
                                                    - **Giải thích:** Có thể do dữ liệu không đủ hoặc các yếu tố khác ảnh hưởng đến sự tương quan.
                                                    - **Lưu ý:** Cần thu thập thêm dữ liệu.
                                                    """
                                        st.markdown(analysis_group, unsafe_allow_html=True)

                                    # Phân tích trạng thái an toàn
                                    if high_oxy.any() and low_co.any() and low_temp.any():
                                        analysis_safe = f"""
                                                    - **😍Trạng thái an toàn:**
                                                    - **Ý nghĩa:** Nhiệt độ thấp, hàm lượng CO thấp và hàm lượng O₂ cao.
                                                    - **Giải thích:** Hệ thống hoạt động bình thường, không có dấu hiệu cháy âm ỉ hay bắn mìn.
                                                    - **Lưu ý:** Tiếp tục theo dõi để đảm bảo tình trạng ổn định.
                                                    """
                                        st.markdown(analysis_safe, unsafe_allow_html=True)
                                    else:
                                        analysis_safe = f"""
                                                    - **😧Không tìm thấy trạng thái an toàn. Có thể do dữ liệu không đủ hoặc các yếu tố khác ảnh hưởng đến sự tương quan.
                                                    - **Lưu ý:** Cần thu thập thêm dữ liệu.
                                                    """
                                        st.markdown(analysis_safe, unsafe_allow_html=True)

                                    # Phân tích trạng thái nguy hiểm
                                    if (high_temp_1 | high_temp_2).any() and (high_co_1 | high_co_2).any() and (
                                            low_oxy_1 | low_oxy_2).any():
                                        analysis_danger = f"""
                                                    - **😰Trạng thái nguy hiểm:**
                                                    - **Ý nghĩa:** Nhiệt độ cao, hàm lượng CO cao và hàm lượng O₂ thấp. Có thể do cháy âm ỉ gây ra sự gia tăng nhiệt độ và hàm lượng CO, đồng thời giảm hàm lượng O₂.
                                                    - **Cảnh báo:** Cần kiểm tra và xử lý tình huống ngay lập tức để đảm bảo an toàn.
                                                    """
                                        st.markdown(analysis_danger, unsafe_allow_html=True)
                                    else:
                                        analysis_danger = f"""
                                                    - 😍Không tìm thấy trạng thái nguy hiểm.
                                                    - **Lưu ý:** Cần thu thập thêm dữ liệu.
                                                    """
                                        st.markdown(analysis_danger, unsafe_allow_html=True)
                        else:
                            st.warning("Không có dữ liệu phù hợp với điều kiện truy vấn. Bạn xem lại đã chọn thời gian đúng chưa, chú ý thời điểm đầu phải trước thời điểm sau nhé!")

# # Nút nhấn để vẽ bản đồ tương quan cho tất cả thông số
# if st.sidebar.button("〽️Vẽ biểu đồ tương quan cho tất cả thông số"):
#     if not kiemtra_thoigian:
#         st.warning("Vui lòng chọn thời gian.")
#         exit()  # Thoát khỏi vòng lặp nếu chưa chọn thời gian
#     try:
#         df = get_data(start_datetime, end_datetime, all_columns)
#         if df.empty:
#             st.warning("Không lấy được dữ liệu từ CSDL.")
#             exit()  # Thoát nếu không lấy được dữ liệu
#         if not df.empty:
#             corr_matrix = df.corr()
#
#             if corr_matrix.empty:
#                 st.warning("Không đủ dữ liệu để tính tương quan.")
#             # Tạo layout 2 cột
#             col1, col2 = st.columns(2)
#
#             with col1:
#                 fig, ax = plt.subplots(figsize=(8, 6))  # Kích thước biểu đồ
#                 sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", center=0, linewidths=.5, square=True,
#                             ax=ax)
#                 ax.set_title("Biểu đồ tương quan")
#                 ax.set_xlabel('Thông số')
#                 ax.set_ylabel('Thông số')
#                 st.pyplot(fig)
#
#             with col2:
#                 # Tìm các cặp tương quan cao
#                 high_corr_pairs = corr_matrix[abs(corr_matrix) > 0.5].stack().sort_values(ascending=False)
#
#                 st.markdown("**📚 Giải thích:**")
#                 for pair in high_corr_pairs.items():
#                     col1, col2 = pair[0]
#                     corr_value = pair[1]
#
#                     st.markdown(f"**Tương quan giữa {col1} và {col2}: {corr_value:.2f}**")
#
#                     if corr_value > 0.7:
#                         st.markdown(
#                             "- **Tương quan mạnh:**  Hai thông số này có mối liên hệ chặt chẽ. Sự thay đổi của một thông số có khả năng tác động mạnh đến thông số kia.")
#                     elif 0.5 <= corr_value <= 0.7:
#                         st.markdown(
#                             "- **Tương quan vừa phải:**  Hai thông số có mối liên hệ khá rõ ràng.  Sự thay đổi của một thông số có thể tác động đến thông số kia, nhưng mức độ không quá mạnh mẽ.")
#                     elif -0.7 < corr_value <= -0.5:
#                         st.markdown(
#                             "- **Tương quan vừa phải (nghịch):** Hai thông số có xu hướng thay đổi theo chiều ngược lại.  Sự thay đổi của một thông số có thể gây ra sự thay đổi theo chiều ngược lại ở thông số kia, nhưng mức độ không quá mạnh.")
#                     elif -0.5 < corr_value <= -0.7:
#                         st.markdown(
#                             "- **Tương quan mạnh (nghịch):** Hai thông số này có mối quan hệ nghịch biến chặt chẽ. Sự thay đổi của một thông số có khả năng tác động mạnh đến sự thay đổi theo chiều ngược lại của thông số kia.")
#                     else:
#                         st.markdown("- **Không có tương quan đáng kể:** Hai thông số này không có mối quan hệ rõ ràng.")
#
#                 # Thêm phần giải thích chung (nếu cần)
#                 st.markdown("- Màu sắc đậm hơn (🔴 hoặc 🔵) cho thấy mức độ tương quan cao hơn.")
#                 st.markdown("- Màu trắng (⚪) cho thấy không có tương quan đáng kể.")
#     except Exception as e:
#         st.error(f"Lỗi: {e}")
# Khung chọn thông số (giữ nguyên)
all_columns = ["NhietDo1Tram1", "NhietDo2Tram1", "NhietDo1Tram2", "NhietDo2Tram2",
               "Co1Tram1", "Co2Tram1", "Co1Tram2", "Co2Tram2",
               "Oxy1Tram1", "Oxy2Tram1", "Oxy1Tram2", "Oxy2Tram2"]

# Kết nối tới cơ sở dữ liệu MySQL
def get_data_all(start_date, end_date, columns):
    conn = mysql.connector.connect(
        host="123.24.206.17",  # Thay thế bằng địa chỉ host thực tế
        port="3306",
        user="admin",
        password="elatec123!",  # Thay thế bằng password thực tế
        database="thantuchay"  # Thay thế bằng tên database thực tế
    )
    try:
        columns_str = ', '.join(columns)
        query = f"""
        SELECT date_time, {columns_str}
        FROM dulieuhalong
        WHERE date_time >= '{start_date}' AND date_time <= '{end_date}'
        """
        df = pd.read_sql(query, conn)
        df['date_time'] = pd.to_datetime(df['date_time'])
        df.set_index('date_time', inplace=True)
        conn.close()
        return df
    except mysql.connector.Error as err:
        st.error(f"Lỗi kết nối CSDL: {err}")
        return pd.DataFrame()  # Trả về DataFrame rỗng nếu có lỗi
# Nút nhấn vẽ biểu đồ tương quan
if st.sidebar.button("📟Vẽ biểu đồ tương quan toàn bộ"):
    if not kiemtra_thoigian:
        st.warning("Vui lòng chọn thời gian.")
        exit()
    try:
        df = get_data_all(start_datetime, end_datetime, all_columns)  # Không lấy date_time

        if df.empty:
            st.warning("Không lấy được dữ liệu từ CSDL.")
            exit()

        corr_matrix = df.corr()

        if corr_matrix.empty:
            st.warning("Không đủ dữ liệu để tính tương quan.")
            exit()  # Thoát nếu không có dữ liệu

        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", center=0, linewidths=.5, square=True, ax=ax)
        ax.set_title("Biểu đồ tương quan")
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Lỗi: {e}")
# Nút nhấn để hiển thị bảng toàn bộ dữ liệu
if st.sidebar.button(" 🔎 Hiển thị bảng toàn bộ dữ liệu cũ"):
    # Kiểm tra xem người dùng đã chọn thời gian chưa
    if not kiemtra_thoigian:
        st.warning("🤭Vui lòng chọn thời gian kết thúc phải lớn hơn thời gian bắt đầu!")
    else:
        with st.spinner('⌛Đang tải dữ liệu...'):
            df = get_data(start_datetime, end_datetime, [col for khu in khu_vuc.values() for col in khu])

            if not df.empty:
                df.fillna(df.mean(), inplace=True)  # Thay thế giá trị NULL bằng trung bình
                df['date_time'] = pd.to_datetime(df['date_time'])  # Chuyển đổi cột thời gian

                # Thêm cột thứ tự
                df.reset_index(inplace=True)
                df['Thứ tự'] = df.index + 1

                # Đổi tên các cột để hiển thị rõ ràng hơn
                new_column_names = {'date_time': 'Thời gian'}
                for khu_name, columns in khu_vuc.items():
                    for col in columns:
                        new_column_names[col] = f"{khu_name} - {col}"
                df.rename(columns=new_column_names, inplace=True)

                # Hiển thị bảng dữ liệu
                st.markdown(f"<h3 style='color: #34dbac;'>📑 Bảng toàn bộ dữ liệu từ {start_datetime} đến {end_datetime}</h3>",
                            unsafe_allow_html=True)
                st.dataframe(df.drop(columns=['index']))  # Bỏ cột index
            else:
                st.warning("😋Không có dữ liệu phù hợp với điều kiện truy vấn. Bạn xem lại đã chọn thời gian đúng chưa, chú ý thời điểm đầu phải trước thời điểm sau nhé!")


# Hiển thị footer
# st.markdown(footer, unsafe_allow_html=True)